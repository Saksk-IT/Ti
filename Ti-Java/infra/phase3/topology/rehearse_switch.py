#!/usr/bin/env python3
"""Rehearse an offline Flask-to-Java cutover or the reverse rollback."""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import json
import os
import pathlib
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from typing import BinaryIO, Mapping, Sequence

from snapshot_bundle import (
    PG_RESTORE_CANONICALIZATION,
    SnapshotError,
    create_bundle,
    hash_file,
    sha256_text,
    utc_now,
    validate_bundle,
)
from topology_guard import (
    ENV_KEYS,
    FORBIDDEN_IDENTITY_TOKEN,
    GuardError,
    GuardedTopology,
    guard_env_file,
)


SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
COMPOSE_FILE = SCRIPT_DIR / "compose.isolated.yml"
SAFE_GENERATION = re.compile(r"[a-z0-9][a-z0-9-]{2,23}")
POSTGRES_RELATION_COUNT_SQL = (
    "SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
    "WHERE n.nspname NOT IN ('pg_catalog','information_schema') "
    "AND n.nspname NOT LIKE 'pg_toast%' AND c.relkind IN ('r','p','S','v','m','f');"
)
PG_RESTRICT = re.compile(rb"^\\restrict ([A-Za-z0-9]{32,128})\r?\n$")
PG_UNRESTRICT = re.compile(rb"^\\unrestrict ([A-Za-z0-9]{32,128})\r?\n$")
PG_STATIC_ARRAY_VALUE = rb"[A-Za-z0-9_-]{1,64}"
PG_SOURCE_ARRAY_ITEM = rb"'(" + PG_STATIC_ARRAY_VALUE + rb")'::character varying"
PG_ROUNDTRIP_ARRAY_ITEM = (
    rb"\('(" + PG_STATIC_ARRAY_VALUE + rb")'::character varying\)::text"
)
PG_CHECK_ARRAY_PREFIX = (
    rb"(?P<prefix>^    CONSTRAINT [a-z_][a-z0-9_]{0,62} CHECK "
    rb"\(\(\([a-z_][a-z0-9_]{0,62}\)::text = ANY \()"
)
PG_CHECK_ARRAY_SUFFIX = rb"(?P<suffix>\)\)\),?\r?\n?)$"
PG_SOURCE_CHECK_ARRAY = re.compile(
    PG_CHECK_ARRAY_PREFIX
    + rb"\(ARRAY\[(?P<items>"
    + PG_SOURCE_ARRAY_ITEM
    + rb"(?:, "
    + PG_SOURCE_ARRAY_ITEM
    + rb"){0,63})\]\)::text\[\]"
    + PG_CHECK_ARRAY_SUFFIX
)
PG_ROUNDTRIP_CHECK_ARRAY = re.compile(
    PG_CHECK_ARRAY_PREFIX
    + rb"ARRAY\[(?P<items>"
    + PG_ROUNDTRIP_ARRAY_ITEM
    + rb"(?:, "
    + PG_ROUNDTRIP_ARRAY_ITEM
    + rb"){0,63})\]"
    + PG_CHECK_ARRAY_SUFFIX
)
PG_SOURCE_ARRAY_ITEM_MATCHER = re.compile(PG_SOURCE_ARRAY_ITEM)
PG_ROUNDTRIP_ARRAY_ITEM_MATCHER = re.compile(PG_ROUNDTRIP_ARRAY_ITEM)
MAX_CANONICAL_LINE_BYTES = 16 * 1024 * 1024
DOCKER_SHA256 = re.compile(r"sha256:[0-9a-f]{64}")
COMPOSE_CONFIG_HASH = re.compile(r"[0-9a-f]{64}")
POSTGRES_IMAGE_REFERENCE = (
    "postgres:18.4-alpine@sha256:"
    "9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
REDIS_IMAGE_REFERENCE = (
    "redis:7.4.7-alpine@sha256:"
    "02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf"
)


class RehearsalError(RuntimeError):
    pass


class CommandError(RehearsalError):
    pass


class PgRestoreCanonicalHasher:
    """Hash pg_restore SQL with two narrow, versioned normalizations."""

    canonicalization = PG_RESTORE_CANONICALIZATION

    def __init__(self) -> None:
        self.digest = hashlib.sha256()
        self.buffer = bytearray()
        self.restrict_token: bytes | None = None
        self.unrestrict_seen = False
        self.line_number = 0

    def _line(self, line: bytes) -> None:
        self.line_number += 1
        restrict = PG_RESTRICT.fullmatch(line)
        unrestrict = PG_UNRESTRICT.fullmatch(line)
        if restrict is not None:
            require(self.restrict_token is None and self.line_number <= 20,
                    "canonical SQL has an unexpected restrict marker")
            self.restrict_token = restrict.group(1)
            self.digest.update(b"\\restrict PHASE3_CANONICAL_V2\n")
            return
        if unrestrict is not None:
            require(self.restrict_token is not None and not self.unrestrict_seen,
                    "canonical SQL has an unexpected unrestrict marker")
            require(unrestrict.group(1) == self.restrict_token,
                    "canonical SQL restrict tokens do not match")
            self.unrestrict_seen = True
            self.digest.update(b"\\unrestrict PHASE3_CANONICAL_V2\n")
            return
        require(not self.unrestrict_seen or not line.strip(),
                "canonical SQL contains content after unrestrict marker")
        self.digest.update(self._canonicalize_static_varchar_text_array(line))

    @staticmethod
    def _canonicalize_static_varchar_text_array(line: bytes) -> bytes:
        """Fold only PostgreSQL's proven static varchar[] -> text[] CHECK rewrite."""
        source = PG_SOURCE_CHECK_ARRAY.fullmatch(line)
        roundtrip = PG_ROUNDTRIP_CHECK_ARRAY.fullmatch(line)
        if source is None and roundtrip is None:
            return line
        require(source is None or roundtrip is None,
                "canonical SQL array rewrite is ambiguous")
        matched = source if source is not None else roundtrip
        assert matched is not None
        item_matcher = PG_SOURCE_ARRAY_ITEM_MATCHER if source is not None \
            else PG_ROUNDTRIP_ARRAY_ITEM_MATCHER
        values = tuple(match.group(1) for match in item_matcher.finditer(matched.group("items")))
        require(values and len(values) <= 64,
                "canonical SQL static array item count is invalid")
        canonical_items = b", ".join(
            b"'" + value + b"'::character varying" for value in values
        )
        return (
            matched.group("prefix")
            + b"(ARRAY["
            + canonical_items
            + b"])::text[]"
            + matched.group("suffix")
        )

    def update(self, chunk: bytes) -> None:
        self.buffer.extend(chunk)
        while True:
            newline = self.buffer.find(b"\n")
            if newline < 0:
                require(len(self.buffer) <= MAX_CANONICAL_LINE_BYTES,
                        "canonical SQL line exceeds the Phase 3 bound")
                return
            line = bytes(self.buffer[:newline + 1])
            del self.buffer[:newline + 1]
            self._line(line)

    def finish(self) -> str:
        if self.buffer:
            self._line(bytes(self.buffer))
            self.buffer.clear()
        require(self.restrict_token is not None and self.unrestrict_seen,
                "canonical SQL guard markers are missing")
        return "sha256:" + self.digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RehearsalError(message)


def digest_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def private_atomic_json(path: pathlib.Path, payload: Mapping[str, object]) -> None:
    require(path.is_absolute(), "report path must be absolute")
    require(not path.exists(), "report overwrite is forbidden")
    require(path.parent.exists() and not path.parent.is_symlink(), "report parent is invalid")
    mode = stat.S_IMODE(path.parent.stat().st_mode)
    require(mode & 0o077 == 0, "report parent must be private")
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


@dataclass(frozen=True)
class Direction:
    operation: str
    source: str
    target: str
    generation: str

    @property
    def source_api(self) -> str:
        return f"{self.source}-api"

    @property
    def source_postgres(self) -> str:
        return f"{self.source}-postgres"

    @property
    def source_redis(self) -> str:
        return f"{self.source}-redis"

    @property
    def target_api(self) -> str:
        return f"{self.target}-api"

    @property
    def target_postgres(self) -> str:
        return f"{self.target}-postgres"

    @property
    def target_redis(self) -> str:
        return f"{self.target}-redis"


@dataclass(frozen=True)
class MountPolicy:
    mount_type: str
    destination: str
    writable: bool
    volume_name: str | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class RuntimeServicePolicy:
    image_reference: str
    mounts: tuple[MountPolicy, ...]
    tmpfs_destinations: frozenset[str]
    networks: Mapping[str, bool]
    container_port: str
    host_port: str
    data_volume: str


class DockerRunner:
    def __init__(self, topology: GuardedTopology, overrides: Mapping[str, str]) -> None:
        self.topology = topology
        self.overrides = dict(overrides)
        environment = dict(os.environ)
        for key in ENV_KEYS:
            environment.pop(key, None)
        environment.update(topology.values)
        environment.update(overrides)
        environment.pop("COMPOSE_FILE", None)
        environment.pop("COMPOSE_PROJECT_NAME", None)
        self.environment = environment
        self.compose_prefix = [
            "docker", "compose",
            "--env-file", str(topology.env_file),
            "--file", str(COMPOSE_FILE),
            "--profile", "runtime",
        ]

    @staticmethod
    def reject_remote_docker_environment() -> None:
        for key in ("DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"):
            require(not os.environ.get(key), f"REMOTE_DOCKER_FORBIDDEN: {key}")

    def _execute(
        self,
        command: Sequence[str],
        *,
        stdin_path: pathlib.Path | None = None,
        stdout_path: pathlib.Path | None = None,
        capture: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        require(all(isinstance(part, str) and part for part in command), "invalid subprocess argument")
        stdin_handle: BinaryIO | None = None
        stdout_handle: BinaryIO | None = None
        try:
            if stdin_path is not None:
                stdin_handle = stdin_path.open("rb")
            if stdout_path is not None:
                descriptor = os.open(stdout_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                stdout_handle = os.fdopen(descriptor, "wb")
            result = subprocess.run(
                list(command),
                stdin=stdin_handle,
                stdout=subprocess.PIPE if capture else stdout_handle or subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                env=self.environment,
                check=False,
                timeout=1800,
            )
        except subprocess.TimeoutExpired as exc:
            raise CommandError("guarded Docker command timed out") from exc
        finally:
            if stdin_handle is not None:
                stdin_handle.close()
            if stdout_handle is not None:
                stdout_handle.close()
        if check and result.returncode != 0:
            raise CommandError(f"guarded Docker command failed with exit {result.returncode}")
        if capture and len(result.stdout) > 64 * 1024:
            raise CommandError("guarded Docker command output exceeded 64 KiB")
        return result

    def docker(self, arguments: Sequence[str], *, capture: bool = False,
               check: bool = True) -> subprocess.CompletedProcess[bytes]:
        return self._execute(["docker", *arguments], capture=capture, check=check)

    def compose(
        self,
        arguments: Sequence[str],
        *,
        stdin_path: pathlib.Path | None = None,
        stdout_path: pathlib.Path | None = None,
        capture: bool = False,
        check: bool = True,
    ) -> subprocess.CompletedProcess[bytes]:
        return self._execute(
            [*self.compose_prefix, *arguments],
            stdin_path=stdin_path,
            stdout_path=stdout_path,
            capture=capture,
            check=check,
        )

    def stream_sha256(
        self,
        arguments: Sequence[str],
        *,
        stdin_path: pathlib.Path | None = None,
        normalize_pg_restore_sql: bool = False,
    ) -> str:
        command = [*self.compose_prefix, *arguments]
        input_context = stdin_path.open("rb") if stdin_path is not None else contextlib.nullcontext(None)
        with input_context as input_handle:
            try:
                process = subprocess.Popen(
                    command,
                    stdin=input_handle,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=self.environment,
                )
            except OSError as exc:
                raise CommandError("could not start guarded Docker stream") from exc
            assert process.stdout is not None
            digest = hashlib.sha256()
            canonical = PgRestoreCanonicalHasher() if normalize_pg_restore_sql else None
            total = 0
            while chunk := process.stdout.read(1024 * 1024):
                total += len(chunk)
                require(total <= 50 * 1024 * 1024 * 1024,
                        "canonical PostgreSQL stream exceeds 50 GiB bound")
                if canonical is None:
                    digest.update(chunk)
                else:
                    canonical.update(chunk)
            _, stderr = process.communicate(timeout=1800)
            if process.returncode != 0:
                raise CommandError(f"guarded Docker stream failed with exit {process.returncode}")
            require(len(stderr) <= 1024 * 1024, "Docker stderr exceeded safety bound")
            require(total > 0, "guarded Docker stream was unexpectedly empty")
            return canonical.finish() if canonical is not None \
                else "sha256:" + digest.hexdigest()

    def preflight_local_context(self) -> None:
        self.reject_remote_docker_environment()
        endpoint = self.docker(
            ["context", "inspect", "--format", "{{.Endpoints.docker.Host}}"], capture=True
        ).stdout.decode("utf-8", "strict").strip()
        require(endpoint.startswith("unix://"), "REMOTE_DOCKER_FORBIDDEN: non-Unix endpoint")
        socket_path = pathlib.Path(endpoint.removeprefix("unix://"))
        require(socket_path.is_absolute(), "Docker Unix socket path must be absolute")
        self.compose(["config", "--quiet"])

    def compose_ids(self, service: str, *, running_only: bool) -> list[str]:
        arguments = ["ps"]
        if running_only:
            arguments += ["--status", "running"]
        else:
            arguments += ["--all"]
        arguments += ["--quiet", service]
        output = self.compose(arguments, capture=True).stdout.decode("ascii", "strict")
        ids = [line.strip() for line in output.splitlines() if line.strip()]
        require(all(re.fullmatch(r"[0-9a-f]{12,64}", value) for value in ids),
                "unexpected Compose container id")
        return ids

    def volume_exists(self, name: str) -> bool:
        result = self.docker(["volume", "inspect", name], check=False)
        require(result.returncode in {0, 1}, "unexpected docker volume inspect result")
        return result.returncode == 0

    def image_id(self, reference: str) -> str:
        value = self.docker(
            ["image", "inspect", "--format", "{{.Id}}", reference], capture=True
        ).stdout.decode("ascii", "strict").strip()
        require(DOCKER_SHA256.fullmatch(value) is not None, "Docker image id is invalid")
        return value

    def container_image_id(self, container_id: str) -> str:
        value = self.docker(
            ["container", "inspect", "--format", "{{.Image}}", container_id], capture=True
        ).stdout.decode("ascii", "strict").strip()
        require(DOCKER_SHA256.fullmatch(value) is not None, "container image id is invalid")
        return value

    def container_json(self, container_id: str, template: str, label: str) -> object:
        raw = self.docker(
            ["container", "inspect", "--format", template, container_id], capture=True
        ).stdout
        try:
            return json.loads(raw.decode("utf-8", "strict"))
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise RehearsalError(f"container {label} is invalid") from exc

    def network_internal(self, name: str) -> bool:
        raw = self.docker(
            ["network", "inspect", "--format", "{{json .Internal}}", name], capture=True
        ).stdout
        try:
            value = json.loads(raw.decode("ascii", "strict"))
        except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
            raise RehearsalError("network internal state is invalid") from exc
        require(isinstance(value, bool), "network internal state is invalid")
        return value


def side_value(topology: GuardedTopology, side: str, suffix: str) -> str:
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return topology.values[f"{prefix}_{suffix}"]


def environment_side_value(values: Mapping[str, str], side: str, suffix: str) -> str:
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return values[f"{prefix}_{suffix}"]


def bind_source_matches(observed: object, expected: str | None) -> bool:
    return isinstance(observed, str) and isinstance(expected, str) \
        and expected.startswith("/") \
        and observed in {expected, "/host_mnt" + expected}


def runtime_service_policy(
    topology: GuardedTopology,
    values: Mapping[str, str],
    service: str,
) -> RuntimeServicePolicy:
    match = re.fullmatch(r"(legacy|java)-(api|postgres|redis)", service)
    require(match is not None, "invalid Phase 3 service identity")
    assert match is not None
    side, kind = match.groups()
    networks = {
        f"{topology.project}-{side}-backend": True,
        f"{topology.project}-{side}-host-access": False,
    }
    if kind == "postgres":
        data_volume = environment_side_value(values, side, "PG_VOLUME")
        mounts = (
            MountPolicy("volume", "/var/lib/postgresql", True, data_volume),
            MountPolicy(
                "bind", "/docker-entrypoint-initdb.d/010-bootstrap-roles.sh", False,
                source_path=str(SCRIPT_DIR / "postgres/010-bootstrap-roles.sh")),
            MountPolicy(
                "bind", "/usr/local/share/grant-after-restore.sql", False,
                source_path=str(SCRIPT_DIR / "postgres/grant-after-restore.sql")),
            MountPolicy(
                "bind", "/run/secrets/db.owner.password", False,
                source_path=environment_side_value(values, side, "DB_OWNER_SECRET_FILE")),
            MountPolicy(
                "bind", "/run/secrets/db.app.password", False,
                source_path=environment_side_value(values, side, "DB_APP_SECRET_FILE")),
            MountPolicy(
                "bind", "/run/secrets/db.audit.password", False,
                source_path=environment_side_value(values, side, "DB_AUDIT_SECRET_FILE")),
        )
        return RuntimeServicePolicy(
            POSTGRES_IMAGE_REFERENCE,
            mounts,
            frozenset({"/tmp", "/var/run/postgresql"}),
            networks,
            "5432/tcp",
            environment_side_value(values, side, "POSTGRES_PORT"),
            data_volume,
        )
    if kind == "redis":
        data_volume = environment_side_value(values, side, "REDIS_VOLUME")
        mounts = (
            MountPolicy("volume", "/data", True, data_volume),
            MountPolicy(
                "bind", "/phase3/redis-entrypoint.sh", False,
                source_path=str(SCRIPT_DIR / "runtime/redis-entrypoint.sh")),
            MountPolicy(
                "bind", "/run/secrets/redis.password", False,
                source_path=environment_side_value(values, side, "REDIS_SECRET_FILE")),
        )
        return RuntimeServicePolicy(
            REDIS_IMAGE_REFERENCE,
            mounts,
            frozenset({"/tmp"}),
            networks,
            "6379/tcp",
            environment_side_value(values, side, "REDIS_PORT"),
            data_volume,
        )

    data_volume = environment_side_value(values, side, "APP_VOLUME")
    if side == "legacy":
        mounts = (
            MountPolicy("volume", "/data", True, data_volume),
            MountPolicy(
                "bind", "/phase3/legacy-entrypoint.sh", False,
                source_path=str(SCRIPT_DIR / "runtime/legacy-entrypoint.sh")),
            MountPolicy(
                "bind", "/run/secrets/db.app.password", False,
                source_path=environment_side_value(values, side, "DB_APP_SECRET_FILE")),
            MountPolicy(
                "bind", "/run/secrets/redis.password", False,
                source_path=environment_side_value(values, side, "REDIS_SECRET_FILE")),
            MountPolicy(
                "bind", "/run/secrets/flask.secret", False,
                source_path=environment_side_value(values, side, "FLASK_SECRET_FILE")),
        )
        container_port = "8000/tcp"
    else:
        mounts = (
            MountPolicy("volume", "/app/data", True, data_volume),
            MountPolicy(
                "bind", "/phase3/java-entrypoint.sh", False,
                source_path=str(SCRIPT_DIR / "runtime/java-entrypoint.sh")),
            MountPolicy(
                "bind", "/run/secrets/ti.db.password", False,
                source_path=environment_side_value(values, side, "DB_APP_SECRET_FILE")),
            MountPolicy(
                "bind", "/run/secrets/ti.redis.password", False,
                source_path=environment_side_value(values, side, "REDIS_SECRET_FILE")),
        )
        container_port = "8080/tcp"
    return RuntimeServicePolicy(
        environment_side_value(values, side, "IMAGE"),
        mounts,
        frozenset({"/tmp"}),
        networks,
        container_port,
        environment_side_value(values, side, "API_PORT"),
        data_volume,
    )


def target_volume_keys(side: str) -> tuple[str, str, str]:
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return (f"{prefix}_PG_VOLUME", f"{prefix}_REDIS_VOLUME", f"{prefix}_APP_VOLUME")


def rollback_overrides(topology: GuardedTopology, generation: str) -> dict[str, str]:
    require(SAFE_GENERATION.fullmatch(generation) is not None, "invalid rollback generation")
    require(FORBIDDEN_IDENTITY_TOKEN.search(generation) is None,
            "PRODUCTION_FORBIDDEN: rollback generation")
    base = f"{topology.project}-rollback-{generation}-legacy"
    values = {
        "TI_PHASE3_LEGACY_PG_VOLUME": f"{base}-pg",
        "TI_PHASE3_LEGACY_REDIS_VOLUME": f"{base}-redis",
        "TI_PHASE3_LEGACY_APP_VOLUME": f"{base}-app",
    }
    require(len(set(values.values())) == 3, "rollback target volumes must differ")
    base_volumes = {topology.values[key] for key in (
        "TI_PHASE3_LEGACY_PG_VOLUME", "TI_PHASE3_LEGACY_REDIS_VOLUME",
        "TI_PHASE3_LEGACY_APP_VOLUME", "TI_PHASE3_JAVA_PG_VOLUME",
        "TI_PHASE3_JAVA_REDIS_VOLUME", "TI_PHASE3_JAVA_APP_VOLUME",
    )}
    require(not base_volumes.intersection(values.values()), "rollback target shares an existing volume")
    return values


@contextlib.contextmanager
def exclusive_run_lock(topology: GuardedTopology):
    lock_path = topology.env_file.parent / "rehearsal.lock"
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(lock_path, flags, 0o600)
    try:
        metadata = os.fstat(descriptor)
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_nlink == 1
                and metadata.st_uid == os.getuid()
                and stat.S_IMODE(metadata.st_mode) == 0o600,
                "rehearsal lock permissions are invalid")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RehearsalError("another rehearsal owns this run directory") from exc
        yield
    finally:
        os.close(descriptor)


class SwitchRehearsal:
    def __init__(self, topology: GuardedTopology, direction: Direction,
                 runner: DockerRunner, confirmation: str) -> None:
        self.topology = topology
        self.direction = direction
        self.runner = runner
        self.confirmation = confirmation
        self.source_stopped = False
        self.target_started = False
        self.target_exposed = False
        self.target_creation_authorized = False
        self.target_volumes_created: list[str] = []
        self.verified_source_postgres_volume: str | None = None
        self.sequence: list[str] = []
        self.run_directory = topology.env_file.parent
        self.snapshot_id = f"{topology.run_id}-{direction.operation.lower()}-{direction.generation}"
        self.snapshot_path = self.run_directory / "snapshots" / self.snapshot_id
        reports = self.run_directory / "reports"
        if not reports.exists():
            reports.mkdir(mode=0o700)
            os.chmod(reports, 0o700)
        require(not reports.is_symlink() and stat.S_IMODE(reports.stat().st_mode) & 0o077 == 0,
                "reports directory is not private")
        self.report_path = reports / f"{direction.operation.lower()}-{direction.generation}.json"

    def expected_confirmation(self) -> str:
        if self.direction.operation == "CUTOVER":
            return f"STOP_LEGACY_CAPTURE_RESTORE_JAVA:{self.topology.run_id}"
        return (
            f"STOP_JAVA_CAPTURE_RESTORE_LEGACY:{self.topology.run_id}:"
            f"{self.direction.generation}"
        )

    def source_volumes(self) -> list[str]:
        return [side_value(self.topology, self.direction.source, suffix)
                for suffix in ("PG_VOLUME", "REDIS_VOLUME", "APP_VOLUME")]

    def target_volumes(self) -> list[str]:
        return [self.runner.environment[key] for key in target_volume_keys(self.direction.target)]

    def _validate_runtime_service(self, service: str) -> str:
        policy = runtime_service_policy(self.topology, self.runner.environment, service)
        all_ids = self.runner.compose_ids(service, running_only=False)
        running_ids = self.runner.compose_ids(service, running_only=True)
        require(len(all_ids) == 1 and running_ids == all_ids,
                f"{service} must have exactly one healthy running container")
        container_id = all_ids[0]

        expected_image = self.runner.image_id(policy.image_reference)
        require(self.runner.container_image_id(container_id) == expected_image,
                f"{service} container does not match the pinned artifact")

        labels = self.runner.container_json(
            container_id, "{{json .Config.Labels}}", f"{service} labels")
        require(isinstance(labels, dict), f"{service} labels are invalid")
        expected_labels = {
            "com.docker.compose.project": self.topology.project,
            "com.docker.compose.service": service,
            "com.docker.compose.oneoff": "False",
            "com.docker.compose.project.config_files": str(COMPOSE_FILE),
            "com.docker.compose.project.working_dir": str(SCRIPT_DIR),
        }
        require(all(labels.get(key) == value for key, value in expected_labels.items()),
                f"{service} Compose labels drifted")
        config_hash = labels.get("com.docker.compose.config-hash")
        require(isinstance(config_hash, str)
                and COMPOSE_CONFIG_HASH.fullmatch(config_hash) is not None,
                f"{service} Compose config hash is invalid")

        state = self.runner.container_json(container_id, "{{json .State}}", f"{service} state")
        require(isinstance(state, dict)
                and state.get("Running") is True
                and state.get("Status") == "running",
                f"{service} is not running")
        health = state.get("Health")
        require(isinstance(health, dict) and health.get("Status") == "healthy",
                f"{service} is not healthy")

        mounts = self.runner.container_json(
            container_id, "{{json .Mounts}}", f"{service} mounts")
        require(isinstance(mounts, list), f"{service} mounts are invalid")
        observed_mounts: dict[str, Mapping[str, object]] = {}
        observed_tmpfs: set[str] = set()
        for mount in mounts:
            require(isinstance(mount, dict), f"{service} mount entry is invalid")
            destination = mount.get("Destination")
            mount_type = mount.get("Type")
            require(isinstance(destination, str) and destination.startswith("/"),
                    f"{service} mount destination is invalid")
            require(destination not in observed_mounts and destination not in observed_tmpfs,
                    f"{service} has duplicate mount destinations")
            if mount_type == "tmpfs":
                require(mount.get("RW") is True, f"{service} tmpfs must be writable")
                observed_tmpfs.add(destination)
            else:
                observed_mounts[destination] = mount
        expected_mounts = {mount.destination: mount for mount in policy.mounts}
        require(set(observed_mounts) == set(expected_mounts),
                f"{service} has missing or extra mounts")
        for destination, expected in expected_mounts.items():
            observed = observed_mounts[destination]
            require(observed.get("Type") == expected.mount_type
                    and observed.get("RW") is expected.writable,
                    f"{service} mount policy drifted at {destination}")
            if expected.mount_type == "volume":
                require(observed.get("Name") == expected.volume_name,
                        f"{service} guarded data volume mount drifted")
            else:
                source = observed.get("Source")
                require(bind_source_matches(source, expected.source_path),
                        f"{service} bind mount source drifted at {destination}")
        host_tmpfs = self.runner.container_json(
            container_id, "{{json .HostConfig.Tmpfs}}", f"{service} tmpfs")
        require(host_tmpfs is None or isinstance(host_tmpfs, dict),
                f"{service} tmpfs configuration is invalid")
        if isinstance(host_tmpfs, dict):
            require(all(isinstance(key, str) and isinstance(value, str)
                        for key, value in host_tmpfs.items()),
                    f"{service} tmpfs configuration is invalid")
            observed_tmpfs.update(host_tmpfs)
        require(observed_tmpfs == set(policy.tmpfs_destinations),
                f"{service} has missing or extra tmpfs mounts")

        networks = self.runner.container_json(
            container_id, "{{json .NetworkSettings.Networks}}", f"{service} networks")
        require(isinstance(networks, dict) and set(networks) == set(policy.networks),
                f"{service} network membership drifted")
        for name, internal in policy.networks.items():
            attachment = networks.get(name)
            network_id = attachment.get("NetworkID") if isinstance(attachment, dict) else None
            require(isinstance(network_id, str)
                    and re.fullmatch(r"[0-9a-f]{64}", network_id) is not None,
                    f"{service} network attachment is invalid")
            require(self.runner.network_internal(name) is internal,
                    f"{service} network internal boundary drifted")

        ports = self.runner.container_json(
            container_id, "{{json .NetworkSettings.Ports}}", f"{service} ports")
        require(isinstance(ports, dict), f"{service} published ports are invalid")
        published = {
            container_port: bindings
            for container_port, bindings in ports.items()
            if bindings is not None
        }
        require(set(published) == {policy.container_port},
                f"{service} has missing or extra published ports")
        bindings = published[policy.container_port]
        require(isinstance(bindings, list) and len(bindings) == 1,
                f"{service} published port binding is invalid")
        binding = bindings[0]
        require(isinstance(binding, dict)
                and binding.get("HostIp") == "127.0.0.1"
                and binding.get("HostPort") == policy.host_port,
                f"{service} published port must match the guarded loopback port")
        return policy.data_volume

    def _validate_source_runtime(self) -> None:
        observed = {
            service: self._validate_runtime_service(service)
            for service in (
                self.direction.source_api,
                self.direction.source_postgres,
                self.direction.source_redis,
            )
        }
        require(observed[self.direction.source_api] == self.source_volumes()[2]
                and observed[self.direction.source_postgres] == self.source_volumes()[0]
                and observed[self.direction.source_redis] == self.source_volumes()[1],
                "source runtime data volumes do not match the guarded snapshot identity")
        self.verified_source_postgres_volume = observed[self.direction.source_postgres]

    def preflight(self) -> None:
        require(self.confirmation == self.expected_confirmation(), "confirmation token mismatch")
        require(not self.report_path.exists(), "rehearsal report already exists")
        require(not self.snapshot_path.exists(), "rehearsal snapshot already exists")
        self.runner.preflight_local_context()
        self._validate_source_runtime()
        for service in (self.direction.target_api, self.direction.target_postgres,
                        self.direction.target_redis):
            require(not self.runner.compose_ids(service, running_only=False),
                    f"target service already has a container: {service}")
        for volume in self.source_volumes():
            require(self.runner.volume_exists(volume), "source volume is missing")
        all_base = {self.topology.values[key] for key in (
            "TI_PHASE3_LEGACY_PG_VOLUME", "TI_PHASE3_LEGACY_REDIS_VOLUME",
            "TI_PHASE3_LEGACY_APP_VOLUME", "TI_PHASE3_JAVA_PG_VOLUME",
            "TI_PHASE3_JAVA_REDIS_VOLUME", "TI_PHASE3_JAVA_APP_VOLUME",
        )}
        targets = self.target_volumes()
        require(len(targets) == len(set(targets)), "target volumes are not distinct")
        require(not set(targets).intersection(self.source_volumes()), "source/target volume sharing")
        if self.direction.operation == "ROLLBACK":
            require(not set(targets).intersection(all_base), "rollback target reused a base volume")
        for volume in targets:
            require(not self.runner.volume_exists(volume), "target volume must not pre-exist")
        self.sequence.append("guarded_inputs_and_fresh_target_verified")

    def stop_source(self) -> str:
        self.runner.compose(["stop", "--timeout", "30", self.direction.source_api])
        self.source_stopped = True
        require(not self.runner.compose_ids(self.direction.source_api, running_only=True),
                "source API did not stop")
        observed = utc_now()
        self.sequence.append("source_api_stopped_and_observed")
        return observed

    def _database_command_values(self, side: str) -> tuple[str, str]:
        owner = side_value(self.topology, side, "DB_OWNER")
        database = side_value(self.topology, side, "DB_NAME")
        return owner, database

    def _pgdump_restrict_key(self) -> str:
        return "PHASE3" + hashlib.sha256(
            f"{self.topology.run_id}:{self.direction.operation}".encode("ascii")
        ).hexdigest()[:32]

    def _dump_database(self, side: str, output_path: pathlib.Path) -> None:
        owner, database = self._database_command_values(side)
        self.runner.compose([
            "exec", "-T", "-e", f"PGDUMP_RESTRICT_KEY={self._pgdump_restrict_key()}",
            f"{side}-postgres", "pg_dump",
            "--format=custom", "--compress=6", "--no-owner", "--no-acl",
            "--username", owner, "--dbname", database,
        ], stdout_path=output_path)

    def _server_version(self, side: str) -> str:
        owner, database = self._database_command_values(side)
        output = self.runner.compose([
            "exec", "-T", f"{side}-postgres", "psql", "--no-psqlrc",
            "--tuples-only", "--no-align", "--username", owner, "--dbname", database,
            "--command", "SHOW server_version_num;",
        ], capture=True).stdout.decode("ascii", "strict").strip()
        require(re.fullmatch(r"[0-9]{6}", output) is not None,
                "source PostgreSQL server_version_num is invalid")
        return output

    def _container_archive_path(self, side: str, purpose: str) -> str:
        token = hashlib.sha256(
            f"{self.topology.run_id}:{self.direction.operation}:{side}:{purpose}".encode("ascii")
        ).hexdigest()[:32]
        return f"/tmp/phase3-{token}.dump"

    def _copy_archive_into_postgres(
        self,
        side: str,
        source: pathlib.Path,
        *,
        purpose: str,
    ) -> str:
        container_path = self._container_archive_path(side, purpose)
        self.runner.compose([
            "exec", "-T", f"{side}-postgres", "sh", "-ec",
            'umask 077; test ! -e "$1"; cat > "$1"; test -s "$1"',
            "phase3-archive-copy", container_path,
        ], stdin_path=source)
        return container_path

    def _remove_container_archive(self, side: str, container_path: str) -> None:
        self.runner.compose([
            "exec", "-T", f"{side}-postgres", "sh", "-ec",
            'rm -f -- "$1"', "phase3-archive-cleanup", container_path,
        ], check=False)

    def _archive_stream_sha256(
        self,
        side: str,
        source: pathlib.Path,
        pg_restore_arguments: Sequence[str],
        *,
        purpose: str,
    ) -> str:
        container_path = self._copy_archive_into_postgres(side, source, purpose=purpose)
        try:
            return self.runner.stream_sha256([
                "exec", "-T", "-e", f"PGDUMP_RESTRICT_KEY={self._pgdump_restrict_key()}",
                f"{side}-postgres", "pg_restore",
                *pg_restore_arguments, container_path,
            ], normalize_pg_restore_sql="--file=-" in pg_restore_arguments)
        finally:
            self._remove_container_archive(side, container_path)

    def _restore_archive(self, side: str, source: pathlib.Path, *, owner: str,
                         database: str) -> None:
        container_path = self._copy_archive_into_postgres(side, source, purpose="restore")
        try:
            self.runner.compose([
                "exec", "-T", f"{side}-postgres", "pg_restore",
                "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
                "--username", owner, "--dbname", database, container_path,
            ])
        finally:
            self._remove_container_archive(side, container_path)

    def capture_snapshot(self, observed_stopped_at: str) -> pathlib.Path:
        require(self.verified_source_postgres_volume == self.source_volumes()[0],
                "source PostgreSQL volume was not verified before snapshot")
        require(not self.runner.compose_ids(self.direction.source_api, running_only=True),
                "source API resumed before snapshot")
        require(self._validate_runtime_service(self.direction.source_postgres)
                == self.verified_source_postgres_volume,
                "source PostgreSQL volume changed before snapshot")
        temporary_dump = self.run_directory / f".{self.snapshot_id}.dump.tmp"
        require(not temporary_dump.exists(), "temporary dump already exists")
        try:
            self._dump_database(self.direction.source, temporary_dump)
            require(not self.runner.compose_ids(self.direction.source_api, running_only=True),
                    "source API resumed during snapshot")
            archive_list_sha256 = self._archive_stream_sha256(
                self.direction.source, temporary_dump, ["--list"], purpose="archive-list",
            )
            canonical_sql_sha256 = self._archive_stream_sha256(
                self.direction.source, temporary_dump,
                ["--no-owner", "--no-acl", "--file=-"],
                purpose="canonical-source",
            )
            server_version_num = self._server_version(self.direction.source)
            require(not self.runner.compose_ids(self.direction.source_api, running_only=True),
                    "source API resumed during snapshot")
            verified_stopped_after_dump_at = utc_now()
            bundle = create_bundle(
                self.topology,
                snapshot_id=self.snapshot_id,
                source_side=self.direction.source,
                target_side=self.direction.target,
                observed_stopped_at=observed_stopped_at,
                verified_stopped_after_dump_at=verified_stopped_after_dump_at,
                server_version_num=server_version_num,
                source_dump=temporary_dump,
                archive_list_sha256=archive_list_sha256,
                canonical_sql_sha256=canonical_sql_sha256,
            )
            validate_bundle(
                self.topology, bundle,
                expected_source=self.direction.source,
                expected_target=self.direction.target,
            )
            self.sequence.append("controlled_snapshot_created_and_validated")
            return bundle
        finally:
            temporary_dump.unlink(missing_ok=True)

    def start_empty_target_data_plane(self) -> None:
        self.target_creation_authorized = True
        try:
            self.runner.compose([
                "up", "--detach", "--wait", "--no-build", "--no-deps",
                self.direction.target_postgres, self.direction.target_redis,
            ])
        finally:
            self.target_volumes_created = [
                volume for volume in self.target_volumes() if self.runner.volume_exists(volume)
            ]
        self.target_started = True
        require(set(self.target_volumes()[:2]).issubset(self.target_volumes_created),
                "target database/cache volumes were not created")
        require(self._validate_runtime_service(self.direction.target_postgres)
                == self.target_volumes()[0],
                "target PostgreSQL volume identity mismatch")
        require(self._validate_runtime_service(self.direction.target_redis)
                == self.target_volumes()[1],
                "target Redis volume identity mismatch")
        owner, database = self._database_command_values(self.direction.target)
        relation_count = self.runner.compose([
            "exec", "-T", self.direction.target_postgres, "psql", "--no-psqlrc",
            "--tuples-only", "--no-align", "--username", owner, "--dbname", database,
            "--command", POSTGRES_RELATION_COUNT_SQL,
        ], capture=True).stdout.decode("ascii", "strict").strip()
        require(relation_count == "0", "target database volume is not empty")
        redis_size = self.runner.compose([
            "exec", "-T", self.direction.target_redis, "sh", "-ec",
            'export REDISCLI_AUTH="$(cat /run/secrets/redis.password)"; '
            'exec redis-cli --no-auth-warning dbsize',
        ], capture=True).stdout.decode("ascii", "strict").strip()
        require(redis_size == "0", "target Redis volume is not empty")
        self.sequence.append("fresh_target_data_plane_started_and_empty")

    def restore_and_verify(self, bundle: pathlib.Path) -> Mapping[str, object]:
        manifest = validate_bundle(
            self.topology, bundle,
            expected_source=self.direction.source,
            expected_target=self.direction.target,
        )
        payload = bundle / "database.dump"
        owner, database = self._database_command_values(self.direction.target)
        self._restore_archive(
            self.direction.target, payload, owner=owner, database=database)

        target_dump = self.run_directory / f".{self.snapshot_id}.target.dump.tmp"
        require(not target_dump.exists(), "target verification dump already exists")
        try:
            self._dump_database(self.direction.target, target_dump)
            target_canonical = self._archive_stream_sha256(
                self.direction.target, target_dump,
                ["--no-owner", "--no-acl", "--file=-"],
                purpose="canonical-target",
            )
        finally:
            target_dump.unlink(missing_ok=True)
        require(target_canonical == manifest["payload"]["canonical_sql_sha256"],
                "restored database semantic fingerprint mismatch")

        app_user = side_value(self.topology, self.direction.target, "DB_APP")
        audit_user = side_value(self.topology, self.direction.target, "DB_AUDIT")
        self.runner.compose([
            "exec", "-T", self.direction.target_postgres, "psql", "--no-psqlrc",
            "--username", owner, "--dbname", database,
            "--set", f"database_name={database}", "--set", f"owner_user={owner}",
            "--set", f"app_user={app_user}", "--set", f"audit_user={audit_user}",
            "--file", "/usr/local/share/grant-after-restore.sql",
        ])
        audit_probe = self.runner.compose([
            "exec", "-T", "-e", "PGPASSWORD_FILE=/run/secrets/db.audit.password",
            self.direction.target_postgres, "sh", "-ec",
            'export PGPASSWORD="$(cat "$PGPASSWORD_FILE")"; '
            'exec psql --no-psqlrc --host 127.0.0.1 --tuples-only --no-align '
            '"$@"', "phase3-audit-probe", "--username", audit_user, "--dbname", database,
            "--command", "SHOW default_transaction_read_only;",
        ], capture=True).stdout.decode("ascii", "strict").strip()
        require(audit_probe == "on", "audit role is not read-only")
        app_probe = self.runner.compose([
            "exec", "-T", "-e", "PGPASSWORD_FILE=/run/secrets/db.app.password",
            self.direction.target_postgres, "sh", "-ec",
            'export PGPASSWORD="$(cat "$PGPASSWORD_FILE")"; '
            'exec psql --no-psqlrc --host 127.0.0.1 --tuples-only --no-align '
            '"$@"', "phase3-app-probe", "--username", app_user, "--dbname", database,
            "--command", "SHOW default_transaction_read_only;",
        ], capture=True).stdout.decode("ascii", "strict").strip()
        require(app_probe == "off", "application role is not writable")
        self.sequence.append("snapshot_restored_transactionally_and_semantically_verified")
        return manifest

    def start_target_api(self) -> None:
        source_services = (
            self.direction.source_api,
            self.direction.source_postgres,
            self.direction.source_redis,
        )
        require(all(not self.runner.compose_ids(service, running_only=False)
                    for service in source_services),
                "source containers must be retired before target exposure")
        # `compose up` may expose the API before it returns. From this point onward,
        # automatic rollback cannot prove that no target write was acknowledged.
        self.target_exposed = True
        self.runner.compose([
            "up", "--detach", "--wait", "--no-build", "--no-deps",
            self.direction.target_api,
        ])
        require(self._validate_runtime_service(self.direction.target_api)
                == self.target_volumes()[2],
                "target application volume identity mismatch")
        require(not self.runner.compose_ids(self.direction.source_api, running_only=True),
                "DUAL_WRITE_FORBIDDEN: both APIs are running")
        self.target_volumes_created = [
            volume for volume in self.target_volumes() if self.runner.volume_exists(volume)
        ]
        require(set(self.target_volumes()).issubset(self.target_volumes_created),
                "target app volume was not created")
        self.sequence.append("target_api_healthy_with_source_retired")

    def retire_source_containers(self) -> None:
        services = [self.direction.source_api, self.direction.source_postgres,
                    self.direction.source_redis]
        self.runner.compose(["stop", "--timeout", "30", *services])
        self.runner.compose(["rm", "--force", "--stop", *services])
        require(all(not self.runner.compose_ids(service, running_only=False) for service in services),
                "source containers were not retired")
        self.sequence.append("source_containers_retired_without_deleting_source_volumes")

    def cleanup_failure(self) -> bool:
        require(not self.target_exposed,
                "automatic cleanup is forbidden after target exposure")
        cleanup_ok = True
        target_services = [self.direction.target_api, self.direction.target_postgres,
                           self.direction.target_redis]
        try:
            stop_result = self.runner.compose(
                ["stop", "--timeout", "15", *target_services], check=False)
            remove_result = self.runner.compose(
                ["rm", "--force", "--stop", *target_services], check=False)
            cleanup_ok = stop_result.returncode == 0 and remove_result.returncode == 0
            if self.runner.compose_ids(self.direction.target_api, running_only=True):
                return False
            owned_target_volumes = [
                volume for volume in self.target_volumes()
                if self.target_creation_authorized and self.runner.volume_exists(volume)
            ]
            for volume in owned_target_volumes:
                if self.runner.volume_exists(volume):
                    result = self.runner.docker(["volume", "rm", volume], check=False)
                    cleanup_ok = cleanup_ok and result.returncode == 0
            if self.source_stopped:
                self.runner.compose([
                    "up", "--detach", "--wait", "--no-build", "--no-deps",
                    self.direction.source_postgres, self.direction.source_redis,
                ])
                self.runner.compose([
                    "up", "--detach", "--wait", "--no-build", "--no-deps",
                    self.direction.source_api,
                ])
                cleanup_ok = cleanup_ok and (
                    len(self.runner.compose_ids(self.direction.source_api, running_only=True)) == 1
                )
                cleanup_ok = cleanup_ok and not self.runner.compose_ids(
                    self.direction.target_api, running_only=True)
        except (RehearsalError, OSError):
            cleanup_ok = False
        return cleanup_ok

    def _base_report(self, *, status_value: str) -> dict[str, object]:
        source_volumes = self.source_volumes()
        target_volumes = self.target_volumes()
        return {
            "schema_version": "1",
            "operation": "CONTROLLED_PHASE3_SWITCH_REHEARSAL",
            "status": status_value,
            "environment": self.topology.environment,
            "run_id": self.topology.run_id,
            "direction": self.direction.operation.lower(),
            "generation": self.direction.generation,
            "source_side": self.direction.source,
            "target_side": self.direction.target,
            "sequence": list(self.sequence),
            "isolation": {
                "source_volume_sha256": [sha256_text(value) for value in source_volumes],
                "target_volume_sha256": [sha256_text(value) for value in target_volumes],
                "volumes_all_distinct": len(set(source_volumes + target_volumes)) == 6,
                "ports_all_distinct": True,
                "networks_are_side_specific": True,
                "redis_was_not_copied": True,
                "application_volume_was_not_copied": True,
            },
            "safety": {
                "confirmation_matched": True,
                "source_stopped_before_snapshot": self.source_stopped,
                "dual_write_observed": False,
                "parent_compose_or_files_touched": False,
                "production_identifiers_accepted": False,
                "snapshot_contains_sensitive_database_data": True,
                "snapshot_and_report_are_git_ignored": True,
            },
        }

    def run(self) -> pathlib.Path:
        self.preflight()
        try:
            observed_stopped_at = self.stop_source()
            bundle = self.capture_snapshot(observed_stopped_at)
            self.start_empty_target_data_plane()
            manifest = self.restore_and_verify(bundle)
            self.retire_source_containers()
            report = self._base_report(status_value="passed")
            report["snapshot"] = {
                "snapshot_id": manifest["snapshot_id"],
                "manifest_sha256": hash_file(bundle / "manifest.json")[0],
                "payload_sha256": manifest["payload"]["sha256"],
                "canonical_sql_sha256": manifest["payload"]["canonical_sql_sha256"],
                "canonicalization": manifest["payload"]["canonicalization"],
            }
            require(all(self.runner.volume_exists(volume) for volume in self.source_volumes()),
                    "source volumes were not preserved")
            require(all(self.runner.volume_exists(volume) for volume in self.target_volumes()[:2]),
                    "target database/cache volumes were not preserved")
            self.start_target_api()
            report["sequence"] = list(self.sequence)
            report["final_state"] = {
                "source_api_running": False,
                "target_api_running": True,
                "source_volumes_preserved": all(
                    self.runner.volume_exists(volume) for volume in self.source_volumes()),
                "target_volumes_present": all(
                    self.runner.volume_exists(volume) for volume in self.target_volumes()),
            }
            require(report["final_state"]["source_volumes_preserved"] is True,
                    "source volumes were not preserved")
            private_atomic_json(self.report_path, report)
            return self.report_path
        except BaseException:
            if self.target_exposed:
                if not self.report_path.exists():
                    failure = self._base_report(status_value="failed")
                    failure["failure"] = {
                        "target_cleanup_attempted": False,
                        "source_restart_attempted": False,
                        "target_data_plane_preserved": True,
                        "manual_intervention_required": True,
                        "error_details_persisted": False,
                    }
                    try:
                        private_atomic_json(self.report_path, failure)
                    except Exception:
                        pass
                raise
            cleanup_ok = self.cleanup_failure()
            if not self.report_path.exists():
                failure = self._base_report(status_value="failed")
                failure["failure"] = {
                    "target_cleanup_attempted": True,
                    "target_cleanup_and_source_restart_succeeded": cleanup_ok,
                    "error_details_persisted": False,
                }
                private_atomic_json(self.report_path, failure)
            raise


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("CUTOVER", "ROLLBACK"))
    parser.add_argument("--env-file", required=True, type=pathlib.Path)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--generation")
    return parser.parse_args(argv)


def build_direction(args: argparse.Namespace) -> Direction:
    if args.operation == "CUTOVER":
        require(args.generation is None, "cutover does not accept a generation")
        return Direction("CUTOVER", "legacy", "java", "initial")
    require(args.generation is not None, "rollback requires --generation")
    require(SAFE_GENERATION.fullmatch(args.generation) is not None, "invalid rollback generation")
    require(FORBIDDEN_IDENTITY_TOKEN.search(args.generation) is None,
            "PRODUCTION_FORBIDDEN: rollback generation")
    return Direction("ROLLBACK", "java", "legacy", args.generation)


def main(argv: Sequence[str] | None = None) -> int:
    try:
        args = parse_args(argv or sys.argv[1:])
        topology = guard_env_file(args.env_file)
        direction = build_direction(args)
        overrides = rollback_overrides(topology, direction.generation) \
            if direction.operation == "ROLLBACK" else {}
        runner = DockerRunner(topology, overrides)
        with exclusive_run_lock(topology):
            report = SwitchRehearsal(topology, direction, runner, args.confirm).run()
        print(report)
        return 0
    except (RehearsalError, GuardError, SnapshotError, OSError, UnicodeError, ValueError) as exc:
        print(f"Phase 3 switch rehearsal failed safely: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
