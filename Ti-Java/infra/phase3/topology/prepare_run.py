#!/usr/bin/env python3
"""Create one private, ignored Phase 3 topology run directory."""

from __future__ import annotations

import argparse
import os
import pathlib
import re
import secrets
import shutil
import sys
from typing import Sequence

from topology_guard import (
    ARTIFACT_ROOT,
    FORBIDDEN_IDENTITY_TOKEN,
    PINNED_IMAGE,
    SAFE_RUN_ID,
    guard_env_file,
)


class PrepareError(RuntimeError):
    pass


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise PrepareError(message)


def _create_private_directory(path: pathlib.Path) -> None:
    path.mkdir(mode=0o700)
    os.chmod(path, 0o700)


def _write_private(path: pathlib.Path, value: str) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="ascii") as handle:
        handle.write(value)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _image(value: str, label: str) -> str:
    _require(PINNED_IMAGE.fullmatch(value) is not None,
             f"{label} must be an immutable sha256 image reference")
    _require(FORBIDDEN_IDENTITY_TOKEN.search(value) is None,
             f"PRODUCTION_FORBIDDEN: {label}")
    return value


def _port(value: int, label: str) -> int:
    _require(1024 <= value <= 65535, f"invalid {label} port")
    return value


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("PREPARE",))
    parser.add_argument("--environment", required=True, choices=("local", "test"))
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--legacy-image", required=True)
    parser.add_argument("--java-image", required=True)
    parser.add_argument("--legacy-api-port", type=int, default=28081)
    parser.add_argument("--java-api-port", type=int, default=28080)
    parser.add_argument("--legacy-postgres-port", type=int, default=35431)
    parser.add_argument("--java-postgres-port", type=int, default=35432)
    parser.add_argument("--legacy-redis-port", type=int, default=36378)
    parser.add_argument("--java-redis-port", type=int, default=36379)
    return parser.parse_args(argv)


def prepare(args: argparse.Namespace) -> pathlib.Path:
    run_id = args.run_id
    _require(SAFE_RUN_ID.fullmatch(run_id) is not None, "invalid run id")
    _require(FORBIDDEN_IDENTITY_TOKEN.search(run_id) is None, "PRODUCTION_FORBIDDEN: run id")
    legacy_image = _image(args.legacy_image, "legacy image")
    java_image = _image(args.java_image, "Java image")
    _require(legacy_image.rsplit("sha256:", 1)[1] != java_image.rsplit("sha256:", 1)[1],
             "legacy and Java image digests must differ")
    ports = [
        _port(args.legacy_api_port, "legacy API"),
        _port(args.java_api_port, "Java API"),
        _port(args.legacy_postgres_port, "legacy PostgreSQL"),
        _port(args.java_postgres_port, "Java PostgreSQL"),
        _port(args.legacy_redis_port, "legacy Redis"),
        _port(args.java_redis_port, "Java Redis"),
    ]
    _require(len(set(ports)) == len(ports), "all host ports must be distinct")

    if not ARTIFACT_ROOT.parent.exists():
        _create_private_directory(ARTIFACT_ROOT.parent)
    elif ARTIFACT_ROOT.parent.is_symlink():
        raise PrepareError("artifact parent symlink is forbidden")
    if not ARTIFACT_ROOT.exists():
        _create_private_directory(ARTIFACT_ROOT)
    _require(ARTIFACT_ROOT.is_dir() and not ARTIFACT_ROOT.is_symlink(),
             "artifact root must be a real directory")

    final_directory = ARTIFACT_ROOT / run_id
    _require(not final_directory.exists(), "run directory already exists")
    staging = ARTIFACT_ROOT / f".{run_id}.{os.getpid()}.tmp"
    _require(not staging.exists(), "staging directory already exists")
    _create_private_directory(staging)
    final_created = False
    try:
        secret_directory = staging / "secrets"
        _create_private_directory(secret_directory)
        secret_names = (
            "legacy-db-owner",
            "legacy-db-app",
            "legacy-db-audit",
            "legacy-redis",
            "legacy-flask",
            "java-db-owner",
            "java-db-app",
            "java-db-audit",
            "java-redis",
        )
        for name in secret_names:
            _write_private(secret_directory / name, secrets.token_urlsafe(48))

        project = f"ti-phase3-{args.environment}-{run_id}"
        role_prefix = re.sub(r"-", "_", f"p3_{run_id}")[:32]
        final_secret_directory = final_directory / "secrets"
        values = {
            "TI_PHASE3_ENVIRONMENT": args.environment,
            "TI_PHASE3_RUN_ID": run_id,
            "TI_PHASE3_PROJECT": project,
            "TI_PHASE3_ARTIFACT_ROOT": str(ARTIFACT_ROOT),
            "TI_PHASE3_LEGACY_IMAGE": legacy_image,
            "TI_PHASE3_JAVA_IMAGE": java_image,
            "TI_PHASE3_LEGACY_API_PORT": str(args.legacy_api_port),
            "TI_PHASE3_JAVA_API_PORT": str(args.java_api_port),
            "TI_PHASE3_LEGACY_POSTGRES_PORT": str(args.legacy_postgres_port),
            "TI_PHASE3_JAVA_POSTGRES_PORT": str(args.java_postgres_port),
            "TI_PHASE3_LEGACY_REDIS_PORT": str(args.legacy_redis_port),
            "TI_PHASE3_JAVA_REDIS_PORT": str(args.java_redis_port),
            "TI_PHASE3_LEGACY_DB_NAME": f"{role_prefix}_legacy_db",
            "TI_PHASE3_JAVA_DB_NAME": f"{role_prefix}_java_db",
            "TI_PHASE3_LEGACY_DB_OWNER": f"{role_prefix}_legacy_owner",
            "TI_PHASE3_LEGACY_DB_APP": f"{role_prefix}_legacy_app",
            "TI_PHASE3_LEGACY_DB_AUDIT": f"{role_prefix}_legacy_audit",
            "TI_PHASE3_JAVA_DB_OWNER": f"{role_prefix}_java_owner",
            "TI_PHASE3_JAVA_DB_APP": f"{role_prefix}_java_app",
            "TI_PHASE3_JAVA_DB_AUDIT": f"{role_prefix}_java_audit",
            "TI_PHASE3_JAVA_SESSION_NAMESPACE":
                f"ti-phase3:{args.environment}:{run_id}:java:sessions",
            "TI_PHASE3_LEGACY_PG_VOLUME": f"{project}-legacy-pg",
            "TI_PHASE3_LEGACY_REDIS_VOLUME": f"{project}-legacy-redis",
            "TI_PHASE3_LEGACY_APP_VOLUME": f"{project}-legacy-app",
            "TI_PHASE3_JAVA_PG_VOLUME": f"{project}-java-pg",
            "TI_PHASE3_JAVA_REDIS_VOLUME": f"{project}-java-redis",
            "TI_PHASE3_JAVA_APP_VOLUME": f"{project}-java-app",
            "TI_PHASE3_LEGACY_DB_OWNER_SECRET_FILE": str(final_secret_directory / "legacy-db-owner"),
            "TI_PHASE3_LEGACY_DB_APP_SECRET_FILE": str(final_secret_directory / "legacy-db-app"),
            "TI_PHASE3_LEGACY_DB_AUDIT_SECRET_FILE": str(final_secret_directory / "legacy-db-audit"),
            "TI_PHASE3_LEGACY_REDIS_SECRET_FILE": str(final_secret_directory / "legacy-redis"),
            "TI_PHASE3_LEGACY_FLASK_SECRET_FILE": str(final_secret_directory / "legacy-flask"),
            "TI_PHASE3_JAVA_DB_OWNER_SECRET_FILE": str(final_secret_directory / "java-db-owner"),
            "TI_PHASE3_JAVA_DB_APP_SECRET_FILE": str(final_secret_directory / "java-db-app"),
            "TI_PHASE3_JAVA_DB_AUDIT_SECRET_FILE": str(final_secret_directory / "java-db-audit"),
            "TI_PHASE3_JAVA_REDIS_SECRET_FILE": str(final_secret_directory / "java-redis"),
        }
        env_file = staging / "compose.env"
        _write_private(env_file, "\n".join(f"{key}={values[key]}" for key in sorted(values)))

        final_directory.mkdir(mode=0o700)
        final_created = True
        os.chmod(final_directory, 0o700)
        os.rename(secret_directory, final_secret_directory)
        os.rename(env_file, final_directory / "compose.env")
        staging.rmdir()
        env_file = final_directory / "compose.env"
        guard_env_file(env_file)
        return env_file
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        if final_created and final_directory.exists():
            shutil.rmtree(final_directory, ignore_errors=True)
        raise


def main(argv: Sequence[str] | None = None) -> int:
    try:
        env_file = prepare(parse_args(argv or sys.argv[1:]))
        print(env_file)
        return 0
    except (PrepareError, OSError, UnicodeError) as exc:
        print(f"Phase 3 run preparation failed: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
