#!/usr/bin/env python3
"""Fail-closed validation for the Phase 3 local/test isolated topology."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
from dataclasses import dataclass
from typing import Mapping, Sequence


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
ARTIFACT_ROOT = SCRIPT_DIR.parent / "artifacts" / "topology"
ALLOWED_ENVIRONMENTS = frozenset({"local", "test"})
FORBIDDEN_IDENTITY_TOKEN = re.compile(r"(?:^|[-_.])(prod(?:uction)?|live)(?:$|[-_.])", re.I)
SAFE_RUN_ID = re.compile(r"[a-z0-9][a-z0-9-]{2,31}")
SAFE_IDENTIFIER = re.compile(r"[a-z][a-z0-9_]{2,62}")
SAFE_VOLUME = re.compile(r"[a-z0-9][a-z0-9_.-]{7,127}")
PINNED_IMAGE = re.compile(r"(?:[a-zA-Z0-9._:/-]+@)?sha256:[0-9a-f]{64}")
SAFE_SECRET = re.compile(r"[A-Za-z0-9_-]{32,128}")

PORT_KEYS = (
    "TI_PHASE3_LEGACY_API_PORT",
    "TI_PHASE3_JAVA_API_PORT",
    "TI_PHASE3_LEGACY_POSTGRES_PORT",
    "TI_PHASE3_JAVA_POSTGRES_PORT",
    "TI_PHASE3_LEGACY_REDIS_PORT",
    "TI_PHASE3_JAVA_REDIS_PORT",
)
VOLUME_KEYS = (
    "TI_PHASE3_LEGACY_PG_VOLUME",
    "TI_PHASE3_LEGACY_REDIS_VOLUME",
    "TI_PHASE3_LEGACY_APP_VOLUME",
    "TI_PHASE3_JAVA_PG_VOLUME",
    "TI_PHASE3_JAVA_REDIS_VOLUME",
    "TI_PHASE3_JAVA_APP_VOLUME",
)
ROLE_KEYS = (
    "TI_PHASE3_LEGACY_DB_OWNER",
    "TI_PHASE3_LEGACY_DB_APP",
    "TI_PHASE3_LEGACY_DB_AUDIT",
    "TI_PHASE3_JAVA_DB_OWNER",
    "TI_PHASE3_JAVA_DB_APP",
    "TI_PHASE3_JAVA_DB_AUDIT",
)
SECRET_KEYS = (
    "TI_PHASE3_LEGACY_DB_OWNER_SECRET_FILE",
    "TI_PHASE3_LEGACY_DB_APP_SECRET_FILE",
    "TI_PHASE3_LEGACY_DB_AUDIT_SECRET_FILE",
    "TI_PHASE3_LEGACY_REDIS_SECRET_FILE",
    "TI_PHASE3_LEGACY_FLASK_SECRET_FILE",
    "TI_PHASE3_JAVA_DB_OWNER_SECRET_FILE",
    "TI_PHASE3_JAVA_DB_APP_SECRET_FILE",
    "TI_PHASE3_JAVA_DB_AUDIT_SECRET_FILE",
    "TI_PHASE3_JAVA_REDIS_SECRET_FILE",
)
ENV_KEYS = frozenset(
    {
        "TI_PHASE3_ENVIRONMENT",
        "TI_PHASE3_RUN_ID",
        "TI_PHASE3_PROJECT",
        "TI_PHASE3_ARTIFACT_ROOT",
        "TI_PHASE3_LEGACY_IMAGE",
        "TI_PHASE3_JAVA_IMAGE",
        "TI_PHASE3_LEGACY_DB_NAME",
        "TI_PHASE3_JAVA_DB_NAME",
        "TI_PHASE3_JAVA_SESSION_NAMESPACE",
        *PORT_KEYS,
        *VOLUME_KEYS,
        *ROLE_KEYS,
        *SECRET_KEYS,
    }
)


class GuardError(RuntimeError):
    """A topology input violated a fail-closed boundary."""


@dataclass(frozen=True)
class GuardedTopology:
    env_file: pathlib.Path
    values: Mapping[str, str]

    @property
    def environment(self) -> str:
        return self.values["TI_PHASE3_ENVIRONMENT"]

    @property
    def run_id(self) -> str:
        return self.values["TI_PHASE3_RUN_ID"]

    @property
    def project(self) -> str:
        return self.values["TI_PHASE3_PROJECT"]


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GuardError(message)


def _lstat_private(path: pathlib.Path, *, directory: bool) -> None:
    try:
        metadata = path.lstat()
    except FileNotFoundError as exc:
        raise GuardError(f"required path does not exist: {path}") from exc
    _require(not stat.S_ISLNK(metadata.st_mode), f"symlink is forbidden: {path}")
    expected_type = stat.S_ISDIR if directory else stat.S_ISREG
    _require(expected_type(metadata.st_mode), f"unexpected path type: {path}")
    _require(metadata.st_uid == os.getuid(), f"path owner mismatch: {path}")
    _require(metadata.st_nlink == (2 if directory else 1) or directory,
             f"hard-linked file is forbidden: {path}")
    _require(stat.S_IMODE(metadata.st_mode) & 0o077 == 0,
             f"group/world permissions are forbidden: {path}")
    if not directory:
        _require(stat.S_IMODE(metadata.st_mode) == 0o600,
                 f"secret/env file must have mode 0600: {path}")


def _inside(child: pathlib.Path, parent: pathlib.Path) -> bool:
    try:
        child.relative_to(parent)
    except ValueError:
        return False
    return True


def load_env_file(path: pathlib.Path) -> dict[str, str]:
    _require(path.is_absolute(), "compose env path must be absolute")
    _lstat_private(path, directory=False)
    values: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        _require(not line.startswith("export "), f"export syntax is forbidden at line {line_number}")
        _require("=" in line, f"invalid env syntax at line {line_number}")
        key, value = line.split("=", 1)
        _require(key in ENV_KEYS, f"unknown env key: {key}")
        _require(key not in values, f"duplicate env key: {key}")
        _require(value == value.strip() and value != "", f"empty or padded env value: {key}")
        _require("\x00" not in value and "\n" not in value and "\r" not in value,
                 f"control byte in env value: {key}")
        values[key] = value
    _require(set(values) == ENV_KEYS,
             f"env keys mismatch; missing={sorted(ENV_KEYS - set(values))}, "
             f"extra={sorted(set(values) - ENV_KEYS)}")
    return values


def guard_env_file(path: pathlib.Path) -> GuardedTopology:
    values = load_env_file(path)
    environment = values["TI_PHASE3_ENVIRONMENT"]
    run_id = values["TI_PHASE3_RUN_ID"]
    project = values["TI_PHASE3_PROJECT"]

    _require(environment in ALLOWED_ENVIRONMENTS, "PRODUCTION_FORBIDDEN: local/test only")
    _require(SAFE_RUN_ID.fullmatch(run_id) is not None, "invalid run id")
    _require(FORBIDDEN_IDENTITY_TOKEN.search(run_id) is None, "PRODUCTION_FORBIDDEN: run id")
    _require(project == f"ti-phase3-{environment}-{run_id}", "project identity mismatch")

    artifact_root = pathlib.Path(values["TI_PHASE3_ARTIFACT_ROOT"])
    _require(artifact_root.is_absolute(), "artifact root must be absolute")
    _require(artifact_root.resolve(strict=True) == ARTIFACT_ROOT.resolve(strict=True),
             "artifact root must be the fixed ignored Phase 3 topology directory")
    _lstat_private(artifact_root, directory=True)
    run_directory = path.parent
    _require(run_directory.parent == artifact_root, "env file must be one level below artifact root")
    _require(run_directory.name == run_id, "run directory must match run id")
    _lstat_private(run_directory, directory=True)

    for image_key in ("TI_PHASE3_LEGACY_IMAGE", "TI_PHASE3_JAVA_IMAGE"):
        image = values[image_key]
        _require(PINNED_IMAGE.fullmatch(image) is not None,
                 f"image must be immutable sha256 reference: {image_key}")
        _require(FORBIDDEN_IDENTITY_TOKEN.search(image) is None,
                 f"PRODUCTION_FORBIDDEN: {image_key}")
    legacy_artifact = values["TI_PHASE3_LEGACY_IMAGE"].rsplit("sha256:", 1)[1]
    java_artifact = values["TI_PHASE3_JAVA_IMAGE"].rsplit("sha256:", 1)[1]
    _require(legacy_artifact != java_artifact, "legacy and Java image digests must differ")

    ports: list[int] = []
    for key in PORT_KEYS:
        try:
            port = int(values[key], 10)
        except ValueError as exc:
            raise GuardError(f"invalid port: {key}") from exc
        _require(1024 <= port <= 65535, f"non-ephemeral-safe port: {key}")
        ports.append(port)
    _require(len(ports) == len(set(ports)), "all legacy/Java host ports must be distinct")

    volumes = [values[key] for key in VOLUME_KEYS]
    _require(len(volumes) == len(set(volumes)), "SHARED_VOLUME_FORBIDDEN")
    for volume in volumes:
        _require(SAFE_VOLUME.fullmatch(volume) is not None, f"invalid volume identity: {volume}")
        _require(volume.startswith(project + "-"), f"volume outside guarded project: {volume}")
        _require(FORBIDDEN_IDENTITY_TOKEN.search(volume) is None, "PRODUCTION_FORBIDDEN: volume")

    database_names = [values["TI_PHASE3_LEGACY_DB_NAME"], values["TI_PHASE3_JAVA_DB_NAME"]]
    _require(len(set(database_names)) == 2, "SHARED_DATABASE_FORBIDDEN")
    for name in [*database_names, *(values[key] for key in ROLE_KEYS)]:
        _require(SAFE_IDENTIFIER.fullmatch(name) is not None, f"invalid PostgreSQL identifier: {name}")
        _require(FORBIDDEN_IDENTITY_TOKEN.search(name) is None, "PRODUCTION_FORBIDDEN: database identity")
    roles = [values[key] for key in ROLE_KEYS]
    _require(len(roles) == len(set(roles)), "all database roles must be distinct")

    namespace = values["TI_PHASE3_JAVA_SESSION_NAMESPACE"]
    _require(namespace == f"ti-phase3:{environment}:{run_id}:java:sessions",
             "Java session namespace mismatch")

    secret_directory = run_directory / "secrets"
    _lstat_private(secret_directory, directory=True)
    secret_paths: list[pathlib.Path] = []
    secret_hashes: set[str] = set()
    for key in SECRET_KEYS:
        secret_path = pathlib.Path(values[key])
        _require(secret_path.is_absolute(), f"secret path must be absolute: {key}")
        _require(_inside(secret_path, secret_directory), f"secret path escaped run directory: {key}")
        _require(secret_path.parent == secret_directory, f"nested secret path is forbidden: {key}")
        _lstat_private(secret_path, directory=False)
        secret = secret_path.read_text(encoding="ascii").rstrip("\r\n")
        _require(SAFE_SECRET.fullmatch(secret) is not None, f"invalid secret encoding: {key}")
        digest = hashlib.sha256(secret.encode("ascii")).hexdigest()
        _require(digest not in secret_hashes, "reused credential is forbidden")
        secret_hashes.add(digest)
        secret_paths.append(secret_path)
    _require(len(secret_paths) == len(set(secret_paths)), "secret files must be distinct")

    return GuardedTopology(env_file=path, values=values)


def redacted_report(topology: GuardedTopology) -> dict[str, object]:
    values = topology.values

    def digest(value: str) -> str:
        return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()

    return {
        "schema_version": "1",
        "operation": "PHASE3_TOPOLOGY_GUARD",
        "environment": topology.environment,
        "run_id": topology.run_id,
        "project_digest": digest(topology.project),
        "image_artifact_sha256": {
            "legacy": "sha256:" + values["TI_PHASE3_LEGACY_IMAGE"].rsplit("sha256:", 1)[1],
            "java": "sha256:" + values["TI_PHASE3_JAVA_IMAGE"].rsplit("sha256:", 1)[1],
        },
        "resource_identity_digests": {
            key: digest(values[key]) for key in (*VOLUME_KEYS, "TI_PHASE3_LEGACY_DB_NAME",
                                                 "TI_PHASE3_JAVA_DB_NAME",
                                                 "TI_PHASE3_JAVA_SESSION_NAMESPACE")
        },
        "ports_are_distinct": True,
        "credentials_are_distinct": True,
        "production_forbidden": True,
        "parent_compose_access": False,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("VALIDATE",))
    parser.add_argument("--env-file", required=True, type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path)
    return parser.parse_args(argv)


def _atomic_json(path: pathlib.Path, payload: Mapping[str, object]) -> None:
    _require(path.is_absolute(), "report path must be absolute")
    _require(not path.exists(), "report overwrite is forbidden")
    _require(path.parent.exists(), "report parent must already exist")
    _require(path.parent.resolve(strict=True) == path.parent, "report parent symlink is forbidden")
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        guarded = guard_env_file(args.env_file)
        report = redacted_report(guarded)
        if args.report:
            _atomic_json(args.report, report)
        else:
            print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0
    except (GuardError, OSError, UnicodeError) as exc:
        print(f"Phase 3 topology guard rejected input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
