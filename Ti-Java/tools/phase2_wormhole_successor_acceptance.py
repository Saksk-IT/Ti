#!/usr/bin/env python3
"""Validate the fixed, append-only Phase 2 WORM evidence chain.

The static infrastructure gate deliberately has no report-path option.  A new
WORM report is accepted only after its path, digest, Java build-context digest,
Dockerfile digest, and predecessor digest are added to ``FIXED_EVIDENCE_CHAIN``.
This keeps historical evidence immutable while allowing reviewed successors.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import datetime as dt
import hashlib
import importlib
import json
from pathlib import Path, PurePosixPath
import re
from typing import Sequence

POSTGRES_IMAGE = (
    "postgres:18.4-alpine@sha256:"
    "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
CAPTURED_AT_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
CANONICAL_SCHEMA_SHA256 = (
    "96a5fda32a6ac4cb1e09cbb8bb0c1c5b33ff6d479cdaefb1d02fcf655a84d38b"
)

HISTORICAL_REPORT_SHA256 = (
    "779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad"
)
HISTORICAL_BUILD_CONTEXT_SHA256 = (
    "7e1da0e1af1d249b6bf5e13d3b6de94ea92920a95620294ffea369e84d448e16"
)
HISTORICAL_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PHASE4C_SUCCESSOR_REPORT_PATH = (
    "docs/refactor/phase4c/personal-bank-user-counts-entry-worm-evidence.json"
)
PHASE4C_SUCCESSOR_REPORT_SHA256 = (
    "cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884"
)
PHASE4C_SUCCESSOR_BUILD_CONTEXT_SHA256 = (
    "c59ee688646b7c23f0f883b4c1377d2a33b507e7dd08b978e98cf3ebdc11825c"
)
PHASE4C_SUCCESSOR_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PHASE4C_READ_REPORT_PATH = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-worm-evidence.json"
)
PHASE4C_READ_REPORT_SHA256 = (
    "fade745bfa0da6ea7d4fc6a16dcee499149ee06dc1113fc92b5256df23cc42e9"
)
PHASE4C_READ_BUILD_CONTEXT_SHA256 = (
    "b616ee8c53eaee58d1771422607d3e9215977a47245aa41e4f3553aee62d64fb"
)
PHASE4C_READ_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PHASE4C_READ_ACCESS_REPORT_PATH = (
    "docs/refactor/phase4c/personal-bank-user-counts-read-access-worm-evidence.json"
)
PHASE4C_READ_ACCESS_REPORT_SHA256 = (
    "a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6"
)
PHASE4C_READ_ACCESS_BUILD_CONTEXT_SHA256 = (
    "935e6a95a33621b01e1e04d752a09513c8037cffe807a73fa1ce9850fb5912f0"
)
PHASE4C_READ_ACCESS_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PHASE4C_HTTP_IMPLEMENTATION_REPORT_PATH = (
    "docs/refactor/phase4c/"
    "personal-bank-user-counts-http-implementation-worm-evidence.json"
)
PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256 = (
    "7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39"
)
PHASE4C_HTTP_IMPLEMENTATION_BUILD_CONTEXT_SHA256 = (
    "273227979fe0ef2efd1724e7f2e6b31b11ce19ebdcf0c262a1ff698dd8f158a3"
)
PHASE4C_HTTP_IMPLEMENTATION_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_PATH = (
    "docs/refactor/phase4c/personal-bank-tag-global-preflight-worm-evidence.json"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_SHA256 = (
    "283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256 = (
    "2b2f2b9956a9188a81606b50405ac82ded0253bbe2539d6fb841575b4c21dcf9"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_PATH = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-global-preflight-hardening-worm-evidence.json"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_SHA256 = (
    "93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256 = (
    "a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17"
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)
PHASE4C_TAG_OPERATOR_CORE_REPORT_PATH = (
    "docs/refactor/phase4c/"
    "personal-bank-tag-migration-operator-core-worm-evidence.json"
)
PHASE4C_TAG_OPERATOR_CORE_REPORT_SHA256 = (
    "db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f"
)
PHASE4C_TAG_OPERATOR_CORE_BUILD_CONTEXT_SHA256 = (
    "29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc"
)
PHASE4C_TAG_OPERATOR_CORE_DOCKERFILE_SHA256 = (
    "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
)

READ_SUCCESSOR_MODULE = "tools.phase4c_read_successor_acceptance"
TARGET_EXECUTION_SUCCESSOR_MODULE = (
    "tools.phase4c_http_target_execution_successor_acceptance"
)
TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE = (
    "tools.phase4c_http_target_execution_post_push_successor_acceptance"
)
TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE = (
    "tools.phase4c_http_target_execution_post_push_anchor_successor_acceptance"
)
TYPED_NORMALIZATION_SUCCESSOR_MODULE = (
    "tools.phase4c_http_typed_normalization_successor_acceptance"
)
TYPED_NORMALIZATION_ANCHOR_SUCCESSOR_MODULE = (
    "tools.phase4c_http_typed_normalization_anchor_successor_acceptance"
)
TAG_GLOBAL_PREFLIGHT_SUCCESSOR_MODULE = (
    "tools.phase4c_tag_migration_global_preflight_successor_acceptance"
)
TAG_OPERATOR_CORE_SUCCESSOR_MODULE = (
    "tools.phase4c_tag_migration_operator_core_successor_acceptance"
)


class EvidenceValidationError(ValueError):
    """A fixed WORM evidence invariant was not satisfied."""


@dataclass(frozen=True)
class EvidenceDescriptor:
    label: str
    relative_path: str
    sha256: str
    build_context_sha256: str
    dockerfile_sha256: str
    predecessor_sha256: str | None


@dataclass(frozen=True)
class ImmutableMirror:
    label: str
    relative_path: str


HISTORICAL_ANCHOR = EvidenceDescriptor(
    label="phase4b-personal-bank-share-list",
    relative_path="infra/phase2/local-reference-verification.json",
    sha256=HISTORICAL_REPORT_SHA256,
    build_context_sha256=HISTORICAL_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=HISTORICAL_DOCKERFILE_SHA256,
    predecessor_sha256=None,
)
PHASE4C_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-user-counts-entry",
    relative_path=PHASE4C_SUCCESSOR_REPORT_PATH,
    sha256=PHASE4C_SUCCESSOR_REPORT_SHA256,
    build_context_sha256=PHASE4C_SUCCESSOR_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_SUCCESSOR_DOCKERFILE_SHA256,
    predecessor_sha256=HISTORICAL_REPORT_SHA256,
)
PHASE4C_READ_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-user-counts-read",
    relative_path=PHASE4C_READ_REPORT_PATH,
    sha256=PHASE4C_READ_REPORT_SHA256,
    build_context_sha256=PHASE4C_READ_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_READ_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_SUCCESSOR_REPORT_SHA256,
)
PHASE4C_READ_ACCESS_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-user-counts-read-access",
    relative_path=PHASE4C_READ_ACCESS_REPORT_PATH,
    sha256=PHASE4C_READ_ACCESS_REPORT_SHA256,
    build_context_sha256=PHASE4C_READ_ACCESS_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_READ_ACCESS_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_READ_REPORT_SHA256,
)
PHASE4C_HTTP_IMPLEMENTATION_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-user-counts-http-implementation",
    relative_path=PHASE4C_HTTP_IMPLEMENTATION_REPORT_PATH,
    sha256=PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256,
    build_context_sha256=PHASE4C_HTTP_IMPLEMENTATION_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_HTTP_IMPLEMENTATION_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_READ_ACCESS_REPORT_SHA256,
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-tag-global-preflight",
    relative_path=PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_PATH,
    sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_SHA256,
    build_context_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256,
)
PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-tag-global-preflight-hardening",
    relative_path=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_PATH,
    sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_SHA256,
    build_context_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_SHA256,
)
PHASE4C_TAG_OPERATOR_CORE_SUCCESSOR = EvidenceDescriptor(
    label="phase4c-personal-bank-tag-migration-operator-core",
    relative_path=PHASE4C_TAG_OPERATOR_CORE_REPORT_PATH,
    sha256=PHASE4C_TAG_OPERATOR_CORE_REPORT_SHA256,
    build_context_sha256=PHASE4C_TAG_OPERATOR_CORE_BUILD_CONTEXT_SHA256,
    dockerfile_sha256=PHASE4C_TAG_OPERATOR_CORE_DOCKERFILE_SHA256,
    predecessor_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_SHA256,
)
FIXED_EVIDENCE_CHAIN = (
    HISTORICAL_ANCHOR,
    PHASE4C_SUCCESSOR,
    PHASE4C_READ_SUCCESSOR,
    PHASE4C_READ_ACCESS_SUCCESSOR,
    PHASE4C_HTTP_IMPLEMENTATION_SUCCESSOR,
    PHASE4C_TAG_GLOBAL_PREFLIGHT_SUCCESSOR,
    PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_SUCCESSOR,
    PHASE4C_TAG_OPERATOR_CORE_SUCCESSOR,
)
FIXED_IMMUTABLE_MIRRORS = (
    ImmutableMirror(
        label="phase4b-personal-bank-share-list-contract-evidence",
        relative_path=(
            "docs/refactor/phase4b/personal-bank-share-list-worm-evidence.json"
        ),
    ),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EvidenceValidationError(message)


def _load_fixed_successor_module(
        qualified_name: str,
        direct_name: str,
        label: str,
) -> object:
    """Lazily import one code-fixed acceptance module, without scanning."""
    try:
        return importlib.import_module(qualified_name)
    except ModuleNotFoundError as error:
        if error.name not in {"tools", qualified_name}:
            raise
    try:
        return importlib.import_module(direct_name)
    except ModuleNotFoundError as error:
        if error.name != direct_name:
            raise
        raise EvidenceValidationError(f"{label} module is required") from error


def _required_loader(module: object, name: str, label: str):
    loader = getattr(module, name, None)
    require(callable(loader), f"{label} loader is required")
    return loader


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path, label: str) -> dict:
    try:
        with path.open("r", encoding="utf-8") as handle:
            document = json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise EvidenceValidationError(f"cannot read {label}: {error}") from error
    require(isinstance(document, dict), f"{label} must be a JSON object")
    return document


def _validated_repo_file(root: Path, relative_path: str, label: str) -> Path:
    require("\\" not in relative_path, f"{label} path must use POSIX separators")
    relative = PurePosixPath(relative_path)
    require(not relative.is_absolute(), f"{label} path must be relative")
    require(
        relative.parts
        and all(part not in ("", ".", "..") for part in relative.parts),
        f"{label} path is not normalized",
    )

    candidate = root.joinpath(*relative.parts)
    cursor = root
    for part in relative.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"{label} path contains a symbolic link")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(root)
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        raise EvidenceValidationError(
            f"{label} must resolve to a file inside Ti-Java"
        ) from error
    require(resolved.is_file(), f"{label} must be a regular file")
    return resolved


def _validate_descriptor(descriptor: EvidenceDescriptor) -> None:
    require(bool(descriptor.label), "evidence label is required")
    require(
        SHA256_PATTERN.fullmatch(descriptor.sha256) is not None,
        f"{descriptor.label} report SHA-256 is not configured",
    )
    require(
        SHA256_PATTERN.fullmatch(descriptor.build_context_sha256) is not None,
        f"{descriptor.label} build-context SHA-256 is not configured",
    )
    require(
        SHA256_PATTERN.fullmatch(descriptor.dockerfile_sha256) is not None,
        f"{descriptor.label} Dockerfile SHA-256 is not configured",
    )
    if descriptor.predecessor_sha256 is not None:
        require(
            SHA256_PATTERN.fullmatch(descriptor.predecessor_sha256) is not None,
            f"{descriptor.label} predecessor SHA-256 is not configured",
        )


def _validate_report(
    report: dict,
    descriptor: EvidenceDescriptor,
    drift_manifest: dict,
) -> None:
    require(
        set(report)
        == {
            "schemaVersion",
            "capturedAt",
            "source",
            "restore",
            "readRole",
            "java",
            "productionDatabaseVersion",
            "flywayBaselineCreated",
        },
        f"{descriptor.label} top-level shape",
    )
    require(report.get("schemaVersion") == 1, f"{descriptor.label} schemaVersion")
    captured_at = report.get("capturedAt")
    require(
        isinstance(captured_at, str)
        and CAPTURED_AT_PATTERN.fullmatch(captured_at) is not None,
        f"{descriptor.label} capturedAt format",
    )
    try:
        dt.datetime.strptime(captured_at, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as error:
        raise EvidenceValidationError(
            f"{descriptor.label} capturedAt value"
        ) from error

    observed = drift_manifest.get("observedReference", {})
    source = report.get("source")
    require(isinstance(source, dict), f"{descriptor.label} source object")
    require(
        set(source)
        == {
            "classification",
            "legacySourceCommit",
            "alembicHead",
            "serverVersion",
            "serverVersionNum",
            "publicBaseTables",
            "publicColumns",
        },
        f"{descriptor.label} source shape",
    )
    require(
        source.get("classification")
        == "explicitly-approved-local-development-reference",
        f"{descriptor.label} source classification",
    )
    require(
        source.get("legacySourceCommit") == drift_manifest.get("legacySourceCommit"),
        f"{descriptor.label} legacy source commit",
    )
    require(
        source.get("alembicHead") == drift_manifest.get("alembicHead"),
        f"{descriptor.label} Alembic head",
    )
    require(
        source.get("serverVersion") == observed.get("postgresVersion"),
        f"{descriptor.label} source version",
    )
    require(
        source.get("serverVersionNum") == str(observed.get("postgresVersionNum")),
        f"{descriptor.label} source version num",
    )
    require(
        source.get("publicBaseTables") == observed.get("physicalTableCount"),
        f"{descriptor.label} source table count",
    )
    require(
        source.get("publicColumns") == observed.get("physicalColumnCount"),
        f"{descriptor.label} source column count",
    )

    restore = report.get("restore")
    require(isinstance(restore, dict), f"{descriptor.label} restore object")
    require(
        set(restore)
        == {
            "image",
            "serverVersion",
            "serverVersionNum",
            "publicBaseTables",
            "publicColumns",
            "canonicalSchemaDumpSha256",
            "schemaDumpPersisted",
        },
        f"{descriptor.label} restore shape",
    )
    require(restore.get("image") == POSTGRES_IMAGE, f"{descriptor.label} restore image")
    require(
        restore.get("serverVersion") == observed.get("postgresVersion"),
        f"{descriptor.label} target version",
    )
    require(
        restore.get("serverVersionNum") == str(observed.get("postgresVersionNum")),
        f"{descriptor.label} target version num",
    )
    require(
        restore.get("publicBaseTables") == observed.get("physicalTableCount"),
        f"{descriptor.label} target table count",
    )
    require(
        restore.get("publicColumns") == observed.get("physicalColumnCount"),
        f"{descriptor.label} target column count",
    )
    require(
        restore.get("canonicalSchemaDumpSha256") == CANONICAL_SCHEMA_SHA256,
        f"{descriptor.label} canonical schema SHA-256",
    )
    require(
        restore.get("schemaDumpPersisted") is False,
        f"{descriptor.label} schema dump cleanup",
    )

    expected_read_role = {
        "selectPassed": True,
        "defaultTransactionReadOnly": True,
        "temporaryPrivilege": False,
        "aclVerifiedWithReadOnlyDefaultDisabled": True,
        "insertRejected": True,
        "updateRejected": True,
        "deleteRejected": True,
        "ddlRejected": True,
        "temporaryDdlRejected": True,
    }
    require(
        report.get("readRole") == expected_read_role,
        f"{descriptor.label} complete read-role ACL evidence",
    )

    java = report.get("java")
    require(isinstance(java, dict), f"{descriptor.label} java object")
    require(
        set(java)
        == {
            "dockerfileSha256",
            "buildContextSha256",
            "hibernateDdlAuto",
            "startupPassed",
            "readinessPassed",
        },
        f"{descriptor.label} Java shape",
    )
    require(
        java.get("dockerfileSha256") == descriptor.dockerfile_sha256,
        f"{descriptor.label} Dockerfile evidence",
    )
    require(
        java.get("buildContextSha256") == descriptor.build_context_sha256,
        f"{descriptor.label} Java build-context evidence",
    )
    require("imageId" not in java, f"{descriptor.label} image ID is forbidden")
    require(
        java.get("hibernateDdlAuto") == "validate",
        f"{descriptor.label} Hibernate mode",
    )
    require(java.get("startupPassed") is True, f"{descriptor.label} Java startup")
    require(java.get("readinessPassed") is True, f"{descriptor.label} readiness")
    require(
        report.get("productionDatabaseVersion") == "unknown",
        f"{descriptor.label} production version boundary",
    )
    require(
        report.get("flywayBaselineCreated") is False,
        f"{descriptor.label} Flyway baseline boundary",
    )

    def values(node):
        if isinstance(node, dict):
            for value in node.values():
                yield from values(value)
        elif isinstance(node, list):
            for value in node:
                yield from values(value)
        else:
            yield node

    strings = [value for value in values(report) if isinstance(value, str)]
    require(
        not any(value.startswith("/") for value in strings),
        f"{descriptor.label} absolute path leaked",
    )
    serialized = json.dumps(report, sort_keys=True).lower()
    for forbidden in ("password", "secret", "ti-postgres-1", "studyuser", "ti_db"):
        require(
            forbidden not in serialized,
            f"{descriptor.label} sensitive/source identifier leaked: {forbidden}",
        )


def validate_evidence_chain(
    ti_java_root: Path,
    drift_manifest_path: Path,
    current_dockerfile_sha256: str,
    current_build_context_sha256: str,
    *,
    chain: Sequence[EvidenceDescriptor],
    immutable_mirrors: Sequence[ImmutableMirror] = (),
) -> EvidenceDescriptor:
    """Validate an explicitly supplied chain; production callers use fixed constants."""

    root = ti_java_root.resolve(strict=True)
    require(root.is_dir(), "Ti-Java root must be a directory")
    require(
        SHA256_PATTERN.fullmatch(current_dockerfile_sha256) is not None,
        "current Dockerfile SHA-256",
    )
    require(
        SHA256_PATTERN.fullmatch(current_build_context_sha256) is not None,
        "current build-context SHA-256",
    )
    require(len(chain) >= 2, "evidence chain must contain an anchor and successor")

    manifest = _load_json(drift_manifest_path, "reference drift manifest")
    paths: set[str] = set()
    digests: set[str] = set()
    build_contexts: set[str] = set()
    previous: EvidenceDescriptor | None = None
    for descriptor in chain:
        _validate_descriptor(descriptor)
        require(descriptor.relative_path not in paths, "duplicate evidence path")
        require(descriptor.sha256 not in digests, "duplicate evidence digest")
        require(
            descriptor.build_context_sha256 not in build_contexts,
            "duplicate evidence build-context",
        )
        if previous is None:
            require(
                descriptor.predecessor_sha256 is None,
                "historical anchor must not have a predecessor",
            )
        else:
            require(
                descriptor.predecessor_sha256 == previous.sha256,
                f"broken predecessor for {descriptor.label}",
            )

        report_path = _validated_repo_file(
            root, descriptor.relative_path, descriptor.label
        )
        require(
            sha256(report_path) == descriptor.sha256,
            f"{descriptor.label} report digest drift",
        )
        _validate_report(_load_json(report_path, descriptor.label), descriptor, manifest)
        paths.add(descriptor.relative_path)
        digests.add(descriptor.sha256)
        build_contexts.add(descriptor.build_context_sha256)
        previous = descriptor

    anchor = chain[0]
    for mirror in immutable_mirrors:
        require(bool(mirror.label), "immutable mirror label is required")
        require(mirror.relative_path not in paths, "duplicate immutable mirror path")
        mirror_path = _validated_repo_file(root, mirror.relative_path, mirror.label)
        require(
            sha256(mirror_path) == anchor.sha256,
            f"{mirror.label} historical mirror digest drift",
        )
        _validate_report(_load_json(mirror_path, mirror.label), anchor, manifest)
        paths.add(mirror.relative_path)

    tip = chain[-1]
    require(
        tip.build_context_sha256 == current_build_context_sha256,
        "fixed WORM successor tip is stale for the current Java build-context",
    )
    require(
        tip.dockerfile_sha256 == current_dockerfile_sha256,
        "fixed WORM successor tip is stale for the current Dockerfile",
    )
    return tip


def validate_fixed_acceptance(
    ti_java_root: Path,
    drift_manifest_path: Path,
    current_dockerfile_sha256: str,
    current_build_context_sha256: str,
) -> EvidenceDescriptor:
    """Validate only the reviewed, fixed production evidence chain."""

    read_successor = _load_fixed_successor_module(
        READ_SUCCESSOR_MODULE,
        "phase4c_read_successor_acceptance",
        "Phase4C fixed read successor acceptance",
    )
    target_successor = _load_fixed_successor_module(
        TARGET_EXECUTION_SUCCESSOR_MODULE,
        "phase4c_http_target_execution_successor_acceptance",
        "Phase4C fixed target-execution successor acceptance",
    )
    post_push_successor = _load_fixed_successor_module(
        TARGET_EXECUTION_POST_PUSH_SUCCESSOR_MODULE,
        "phase4c_http_target_execution_post_push_successor_acceptance",
        "Phase4C fixed target-execution post-push successor acceptance",
    )
    post_push_anchor_successor = _load_fixed_successor_module(
        TARGET_EXECUTION_POST_PUSH_ANCHOR_SUCCESSOR_MODULE,
        "phase4c_http_target_execution_post_push_anchor_successor_acceptance",
        "Phase4C fixed target-execution post-push anchor successor acceptance",
    )
    typed_normalization_successor = _load_fixed_successor_module(
        TYPED_NORMALIZATION_SUCCESSOR_MODULE,
        "phase4c_http_typed_normalization_successor_acceptance",
        "Phase4C fixed HTTP typed-normalization successor acceptance",
    )
    typed_normalization_anchor_successor = _load_fixed_successor_module(
        TYPED_NORMALIZATION_ANCHOR_SUCCESSOR_MODULE,
        "phase4c_http_typed_normalization_anchor_successor_acceptance",
        "Phase4C fixed HTTP typed-normalization anchor successor acceptance",
    )
    tag_global_preflight_successor = _load_fixed_successor_module(
        TAG_GLOBAL_PREFLIGHT_SUCCESSOR_MODULE,
        "phase4c_tag_migration_global_preflight_successor_acceptance",
        "Phase4C fixed tag global-preflight successor acceptance",
    )

    load_read_successor_contract = _required_loader(
        read_successor,
        "load_read_successor_contract",
        "Phase4C fixed read successor acceptance",
    )
    load_http_target_execution_successor_contract = _required_loader(
        target_successor,
        "load_http_target_execution_successor_contract",
        "Phase4C fixed target-execution successor acceptance",
    )
    load_http_target_execution_post_push_successor = _required_loader(
        post_push_successor,
        "load",
        "Phase4C fixed target-execution post-push successor acceptance",
    )
    load_http_target_execution_post_push_anchor_successor = _required_loader(
        post_push_anchor_successor,
        "load",
        "Phase4C fixed target-execution post-push anchor successor acceptance",
    )
    load_http_typed_normalization_successor = _required_loader(
        typed_normalization_successor,
        "load",
        "Phase4C fixed HTTP typed-normalization successor acceptance",
    )
    load_http_typed_normalization_anchor_successor = _required_loader(
        typed_normalization_anchor_successor,
        "load",
        "Phase4C fixed HTTP typed-normalization anchor successor acceptance",
    )
    load_tag_global_preflight_successor = _required_loader(
        tag_global_preflight_successor,
        "load",
        "Phase4C fixed tag global-preflight successor acceptance",
    )

    require(
        isinstance(load_read_successor_contract(ti_java_root), dict),
        "Phase4C fixed read successor contract is required",
    )
    require(
        isinstance(
            load_http_target_execution_successor_contract(ti_java_root),
            dict,
        ),
        "Phase4C fixed target-execution successor contract is required",
    )
    require(
        isinstance(
            load_http_target_execution_post_push_successor(ti_java_root),
            dict,
        ),
        "Phase4C fixed target-execution post-push successor contract is required",
    )
    require(
        isinstance(
            load_http_target_execution_post_push_anchor_successor(ti_java_root),
            dict,
        ),
        "Phase4C fixed target-execution post-push anchor successor contract is required",
    )
    require(
        isinstance(load_http_typed_normalization_successor(ti_java_root), dict),
        "Phase4C fixed HTTP typed-normalization successor contract is required",
    )
    require(
        isinstance(
            load_http_typed_normalization_anchor_successor(ti_java_root),
            dict,
        ),
        "Phase4C fixed HTTP typed-normalization anchor successor contract is required",
    )
    require(
        isinstance(load_tag_global_preflight_successor(ti_java_root), dict),
        "Phase4C fixed tag global-preflight successor contract is required",
    )
    tag_operator_core_successor = _load_fixed_successor_module(
        TAG_OPERATOR_CORE_SUCCESSOR_MODULE,
        "phase4c_tag_migration_operator_core_successor_acceptance",
        "Phase4C fixed tag operator-core successor acceptance",
    )
    load_tag_operator_core_successor = _required_loader(
        tag_operator_core_successor,
        "load",
        "Phase4C fixed tag operator-core successor acceptance",
    )
    require(
        isinstance(load_tag_operator_core_successor(ti_java_root), dict),
        "Phase4C fixed tag operator-core successor contract is required",
    )

    return validate_fixed_chain(
        ti_java_root,
        drift_manifest_path,
        current_dockerfile_sha256,
        current_build_context_sha256,
    )


def validate_fixed_chain(
    ti_java_root: Path,
    drift_manifest_path: Path,
    current_dockerfile_sha256: str,
    current_build_context_sha256: str,
) -> EvidenceDescriptor:
    """Validate fixed physical WORM bytes without importing successor contracts.

    Terminal contract builders use this independent path to bind the reviewed
    chain tip without recursively loading their own acceptance module.  The
    production static gate calls ``validate_fixed_acceptance`` and therefore
    additionally requires every code-fixed logical successor contract.
    """

    return validate_evidence_chain(
        ti_java_root,
        drift_manifest_path,
        current_dockerfile_sha256,
        current_build_context_sha256,
        chain=FIXED_EVIDENCE_CHAIN,
        immutable_mirrors=FIXED_IMMUTABLE_MIRRORS,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the fixed Phase 2 WORM successor evidence chain."
    )
    parser.add_argument("--ti-java-root", type=Path, required=True)
    parser.add_argument("--drift-manifest", type=Path, required=True)
    parser.add_argument("--dockerfile-sha256", required=True)
    parser.add_argument("--build-context-sha256", required=True)
    args = parser.parse_args()

    try:
        tip = validate_fixed_acceptance(
            args.ti_java_root,
            args.drift_manifest,
            args.dockerfile_sha256,
            args.build_context_sha256,
        )
    except (EvidenceValidationError, OSError) as error:
        raise SystemExit(f"Wormhole evidence invalid: {error}") from error
    print(f"Fixed WORM successor evidence passed: {tip.label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
