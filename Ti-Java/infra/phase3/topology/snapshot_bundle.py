#!/usr/bin/env python3
"""Create and validate sensitive Phase 3 PostgreSQL snapshot bundles."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import stat
import sys
from typing import BinaryIO, Mapping, Sequence

from topology_guard import GuardedTopology, guard_env_file


MANIFEST_NAME = "manifest.json"
PAYLOAD_NAME = "database.dump"
MAX_DUMP_BYTES = 10 * 1024 * 1024 * 1024
PG_RESTORE_CANONICALIZATION = (
    "pg-restore-sql-v2-restrict-token-static-ascii-varchar-text-array"
)
TOP_LEVEL_KEYS = frozenset({
    "schema_version", "snapshot_id", "environment", "run_id", "scope",
    "source_side", "target_side", "created_at", "source_quiescence",
    "source_identity", "postgres", "payload", "redis_policy",
    "application_volume_policy",
})
SHA256_TEXT = __import__("re").compile(r"sha256:[0-9a-f]{64}")
SNAPSHOT_ID = __import__("re").compile(r"[a-z0-9][a-z0-9-]{2,95}")


class SnapshotError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SnapshotError(message)


def sha256_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def image_artifact_sha256(reference: str) -> str:
    return "sha256:" + reference.rsplit("sha256:", 1)[1]


def hash_file(path: pathlib.Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            size += len(chunk)
            require(size <= MAX_DUMP_BYTES, "snapshot payload exceeds 10 GiB Phase 3 bound")
            digest.update(chunk)
    return "sha256:" + digest.hexdigest(), size


def has_custom_dump_magic(path: pathlib.Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(5) == b"PGDMP"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_timestamp(value: object, label: str) -> dt.datetime:
    require(isinstance(value, str), f"{label} must be a string")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SnapshotError(f"{label} is not RFC3339") from exc
    require(parsed.tzinfo is not None and parsed.utcoffset() == dt.timedelta(0),
            f"{label} must be UTC")
    return parsed


def private_path(path: pathlib.Path, *, directory: bool) -> os.stat_result:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise SnapshotError(f"snapshot path is missing: {path}") from exc
    require(not stat.S_ISLNK(metadata.st_mode), f"snapshot symlink is forbidden: {path}")
    require((stat.S_ISDIR if directory else stat.S_ISREG)(metadata.st_mode),
            f"snapshot path type is invalid: {path}")
    require(metadata.st_uid == os.getuid(), f"snapshot owner mismatch: {path}")
    require(stat.S_IMODE(metadata.st_mode) & 0o077 == 0,
            f"snapshot group/world permissions are forbidden: {path}")
    if not directory:
        require(metadata.st_nlink == 1, f"hard-linked snapshot file is forbidden: {path}")
        require(stat.S_IMODE(metadata.st_mode) == 0o600,
                f"snapshot file must have mode 0600: {path}")
    return metadata


def snapshot_root(topology: GuardedTopology) -> pathlib.Path:
    root = topology.env_file.parent / "snapshots"
    if not root.exists():
        root.mkdir(mode=0o700)
        os.chmod(root, 0o700)
    private_path(root, directory=True)
    require(root.parent == topology.env_file.parent, "snapshot root escaped run directory")
    return root


def _exact_object(value: object, expected: set[str], label: str) -> Mapping[str, object]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == expected, f"{label} keys mismatch")
    return value


def _digest(value: object, label: str) -> str:
    require(isinstance(value, str) and SHA256_TEXT.fullmatch(value) is not None,
            f"{label} must be sha256")
    return value


def validate_manifest(
    manifest: object,
    topology: GuardedTopology,
    *,
    expected_source: str,
    expected_target: str,
) -> Mapping[str, object]:
    require(isinstance(manifest, dict) and set(manifest) == TOP_LEVEL_KEYS,
            "manifest top-level contract mismatch")
    require(manifest["schema_version"] == "1", "manifest schema version mismatch")
    snapshot_id = manifest["snapshot_id"]
    require(isinstance(snapshot_id, str) and SNAPSHOT_ID.fullmatch(snapshot_id) is not None,
            "snapshot id is invalid")
    require(manifest["environment"] == topology.environment, "snapshot environment mismatch")
    require(manifest["run_id"] == topology.run_id, "snapshot run id mismatch")
    require(manifest["scope"] == "phase3-auth-postgresql-only", "snapshot scope mismatch")
    require(manifest["source_side"] == expected_source, "snapshot source mismatch")
    require(manifest["target_side"] == expected_target, "snapshot target mismatch")
    require(expected_source in {"legacy", "java"} and expected_target in {"legacy", "java"}
            and expected_source != expected_target, "invalid expected sides")

    created_at = parse_timestamp(manifest["created_at"], "created_at")
    require(created_at <= dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=30),
            "snapshot creation time is in the future")
    quiescence = _exact_object(
        manifest["source_quiescence"],
        {"method", "service", "observed_at", "verified_after_dump_at",
         "running_container_count", "project_sha256"},
        "source_quiescence",
    )
    require(quiescence["method"] == "compose-service-stopped-before-pg-dump",
            "quiescence method mismatch")
    require(quiescence["service"] == f"{expected_source}-api", "quiescence service mismatch")
    require(quiescence["running_container_count"] == 0, "source was not quiescent")
    require(quiescence["project_sha256"] == sha256_text(topology.project),
            "quiescence project mismatch")
    observed_at = parse_timestamp(quiescence["observed_at"], "source_quiescence.observed_at")
    verified_after_dump_at = parse_timestamp(
        quiescence["verified_after_dump_at"], "source_quiescence.verified_after_dump_at")
    require(observed_at <= verified_after_dump_at <= created_at,
            "snapshot quiescence timestamps are out of order")
    require(created_at <= verified_after_dump_at + dt.timedelta(minutes=5),
            "snapshot manifest was not sealed promptly after the post-dump stop check")

    source_identity = _exact_object(
        manifest["source_identity"],
        {"artifact_sha256", "database_sha256", "postgres_volume_sha256"},
        "source_identity",
    )
    for key, value in source_identity.items():
        _digest(value, f"source_identity.{key}")
    values = topology.values
    image_key = "TI_PHASE3_LEGACY_IMAGE" if expected_source == "legacy" else "TI_PHASE3_JAVA_IMAGE"
    db_key = "TI_PHASE3_LEGACY_DB_NAME" if expected_source == "legacy" else "TI_PHASE3_JAVA_DB_NAME"
    volume_key = "TI_PHASE3_LEGACY_PG_VOLUME" if expected_source == "legacy" else "TI_PHASE3_JAVA_PG_VOLUME"
    require(source_identity["artifact_sha256"] == image_artifact_sha256(values[image_key]),
            "source artifact identity mismatch")
    require(source_identity["database_sha256"] == sha256_text(values[db_key]),
            "source database identity mismatch")
    require(source_identity["postgres_volume_sha256"] == sha256_text(values[volume_key]),
            "source volume identity mismatch")

    postgres = _exact_object(
        manifest["postgres"],
        {"server_version_num", "dump_format", "no_owner", "no_acl", "single_database"},
        "postgres",
    )
    require(postgres["server_version_num"] == "180004",
            "snapshot PostgreSQL version does not match the pinned topology")
    require(postgres["dump_format"] == "custom", "snapshot must use custom pg_dump")
    require(postgres["no_owner"] is True and postgres["no_acl"] is True
            and postgres["single_database"] is True, "unsafe pg_dump policy")

    payload = _exact_object(
        manifest["payload"],
        {"path", "size_bytes", "sha256", "archive_list_sha256", "canonical_sql_sha256",
         "canonicalization"},
        "payload",
    )
    require(payload["path"] == PAYLOAD_NAME, "snapshot payload path mismatch")
    require(type(payload["size_bytes"]) is int and 5 <= payload["size_bytes"] <= MAX_DUMP_BYTES,
            "snapshot payload size is invalid")
    for key in ("sha256", "archive_list_sha256", "canonical_sql_sha256"):
        _digest(payload[key], f"payload.{key}")
    require(payload["canonicalization"] == PG_RESTORE_CANONICALIZATION,
            "snapshot canonicalization contract mismatch")

    redis_policy = _exact_object(
        manifest["redis_policy"], {"copied", "target_start_state"}, "redis_policy")
    require(redis_policy == {"copied": False, "target_start_state": "fresh-empty-volume"},
            "Redis must start from a fresh empty independent volume")
    app_policy = _exact_object(
        manifest["application_volume_policy"],
        {"copied", "target_start_state", "reason"},
        "application_volume_policy",
    )
    require(app_policy == {
        "copied": False,
        "target_start_state": "fresh-empty-volume",
        "reason": "phase3-auth-scope-has-no-file-payload",
    }, "application volume policy mismatch")
    return manifest


def validate_bundle(
    topology: GuardedTopology,
    bundle: pathlib.Path,
    *,
    expected_source: str,
    expected_target: str,
) -> Mapping[str, object]:
    require(bundle.is_absolute(), "snapshot bundle path must be absolute")
    root = snapshot_root(topology)
    require(bundle.parent == root, "snapshot bundle must be a direct child of the guarded snapshot root")
    private_path(bundle, directory=True)
    names = {entry.name for entry in bundle.iterdir()}
    require(names == {MANIFEST_NAME, PAYLOAD_NAME}, "snapshot bundle has missing or extra files")
    manifest_path = bundle / MANIFEST_NAME
    payload_path = bundle / PAYLOAD_NAME
    manifest_metadata = private_path(manifest_path, directory=False)
    require(1 <= manifest_metadata.st_size <= 64 * 1024,
            "snapshot manifest exceeds the 64 KiB bound")
    private_path(payload_path, directory=False)
    require(has_custom_dump_magic(payload_path), "snapshot is not a PostgreSQL custom archive")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SnapshotError("snapshot manifest JSON is invalid") from exc
    validated = validate_manifest(
        manifest, topology, expected_source=expected_source, expected_target=expected_target)
    require(bundle.name == validated["snapshot_id"], "snapshot directory/id mismatch")
    digest, size = hash_file(payload_path)
    payload = validated["payload"]
    require(payload["sha256"] == digest, "snapshot checksum mismatch")
    require(payload["size_bytes"] == size, "snapshot size mismatch")
    return validated


def create_bundle(
    topology: GuardedTopology,
    *,
    snapshot_id: str,
    source_side: str,
    target_side: str,
    observed_stopped_at: str,
    verified_stopped_after_dump_at: str,
    server_version_num: str,
    source_dump: pathlib.Path,
    archive_list_sha256: str,
    canonical_sql_sha256: str,
) -> pathlib.Path:
    require(SNAPSHOT_ID.fullmatch(snapshot_id) is not None, "snapshot id is invalid")
    require(source_side in {"legacy", "java"} and target_side in {"legacy", "java"}
            and source_side != target_side, "snapshot sides are invalid")
    _digest(archive_list_sha256, "archive_list_sha256")
    _digest(canonical_sql_sha256, "canonical_sql_sha256")
    require(source_dump.is_absolute(), "source dump path must be absolute")
    source_metadata = private_path(source_dump, directory=False)
    require(5 <= source_metadata.st_size <= MAX_DUMP_BYTES,
            "source dump size is outside the Phase 3 bound")
    require(has_custom_dump_magic(source_dump), "source dump is not a custom archive")
    root = snapshot_root(topology)
    final_bundle = root / snapshot_id
    require(not final_bundle.exists(), "snapshot bundle overwrite is forbidden")
    staging = root / f".{snapshot_id}.{os.getpid()}.tmp"
    require(not staging.exists(), "snapshot staging path already exists")
    staging.mkdir(mode=0o700)
    os.chmod(staging, 0o700)
    try:
        payload_path = staging / PAYLOAD_NAME
        descriptor = os.open(payload_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "wb") as destination, source_dump.open("rb") as source:
            shutil.copyfileobj(source, destination, 1024 * 1024)
            destination.flush()
            os.fsync(destination.fileno())
        digest, size = hash_file(payload_path)
        values = topology.values
        image_key = "TI_PHASE3_LEGACY_IMAGE" if source_side == "legacy" else "TI_PHASE3_JAVA_IMAGE"
        db_key = "TI_PHASE3_LEGACY_DB_NAME" if source_side == "legacy" else "TI_PHASE3_JAVA_DB_NAME"
        volume_key = "TI_PHASE3_LEGACY_PG_VOLUME" if source_side == "legacy" else "TI_PHASE3_JAVA_PG_VOLUME"
        manifest = {
            "schema_version": "1",
            "snapshot_id": snapshot_id,
            "environment": topology.environment,
            "run_id": topology.run_id,
            "scope": "phase3-auth-postgresql-only",
            "source_side": source_side,
            "target_side": target_side,
            "created_at": utc_now(),
            "source_quiescence": {
                "method": "compose-service-stopped-before-pg-dump",
                "service": f"{source_side}-api",
                "observed_at": observed_stopped_at,
                "verified_after_dump_at": verified_stopped_after_dump_at,
                "running_container_count": 0,
                "project_sha256": sha256_text(topology.project),
            },
            "source_identity": {
                "artifact_sha256": image_artifact_sha256(values[image_key]),
                "database_sha256": sha256_text(values[db_key]),
                "postgres_volume_sha256": sha256_text(values[volume_key]),
            },
            "postgres": {
                "server_version_num": server_version_num,
                "dump_format": "custom",
                "no_owner": True,
                "no_acl": True,
                "single_database": True,
            },
            "payload": {
                "path": PAYLOAD_NAME,
                "size_bytes": size,
                "sha256": digest,
                "archive_list_sha256": archive_list_sha256,
                "canonical_sql_sha256": canonical_sql_sha256,
                "canonicalization": PG_RESTORE_CANONICALIZATION,
            },
            "redis_policy": {"copied": False, "target_start_state": "fresh-empty-volume"},
            "application_volume_policy": {
                "copied": False,
                "target_start_state": "fresh-empty-volume",
                "reason": "phase3-auth-scope-has-no-file-payload",
            },
        }
        validate_manifest(manifest, topology, expected_source=source_side, expected_target=target_side)
        manifest_path = staging / MANIFEST_NAME
        manifest_descriptor = os.open(manifest_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(manifest_descriptor, "w", encoding="utf-8") as handle:
            json.dump(manifest, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        final_bundle.mkdir(mode=0o700)
        os.chmod(final_bundle, 0o700)
        try:
            os.link(manifest_path, final_bundle / MANIFEST_NAME)
            os.link(payload_path, final_bundle / PAYLOAD_NAME)
        except BaseException:
            shutil.rmtree(final_bundle, ignore_errors=True)
            raise
        manifest_path.unlink()
        payload_path.unlink()
        staging.rmdir()
        validate_bundle(topology, final_bundle, expected_source=source_side, expected_target=target_side)
        return final_bundle
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("VALIDATE",))
    parser.add_argument("--env-file", required=True, type=pathlib.Path)
    parser.add_argument("--bundle", required=True, type=pathlib.Path)
    parser.add_argument("--expected-source", required=True, choices=("legacy", "java"))
    parser.add_argument("--expected-target", required=True, choices=("legacy", "java"))
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        topology = guard_env_file(args.env_file)
        manifest = validate_bundle(
            topology,
            args.bundle,
            expected_source=args.expected_source,
            expected_target=args.expected_target,
        )
        print(json.dumps({
            "schema_version": "1",
            "operation": "VALIDATE_PHASE3_SNAPSHOT",
            "snapshot_id": manifest["snapshot_id"],
            "payload_sha256": manifest["payload"]["sha256"],
            "valid": True,
        }, sort_keys=True))
        return 0
    except (SnapshotError, OSError, UnicodeError, ValueError) as exc:
        print(f"Phase 3 snapshot rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
