#!/usr/bin/env python3
"""Fail-closed runtime-state auditor for Phase 3 local/test READ_COMPARE runs."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import stat
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping

from rehearse_switch import DockerRunner, RehearsalError
from topology_guard import GuardError, GuardedTopology, guard_env_file


AUDITOR_ID = "phase3-runtime-state-auditor-v2"
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
POSTGRES_IMAGE = (
    "postgres:18.4-alpine@"
    "sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15"
)
REDIS_IMAGE = (
    "redis:7.4.7-alpine@"
    "sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf"
)
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
CONTAINER_ID = re.compile(r"[0-9a-f]{12,64}\Z")
ENVIRONMENT_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
CONTAINER_PORT = re.compile(r"[1-9][0-9]{0,4}/tcp\Z")
REDIS_ROW = re.compile(
    r"[0-9a-f]{40}\|(string|list|set|zset|hash|stream)\|(-1|[1-9][0-9]*)\|[0-9a-f]{40}\Z"
)
ALLOWED_PHASES = frozenset({"before", "after"})
SIDE_ENV_FILES = {
    "legacy": "TI_PHASE3_AUDIT_LEGACY_ENV_FILE",
    "java": "TI_PHASE3_AUDIT_JAVA_ENV_FILE",
}

PG_DATA_POLICY = {
    "version": "phase3-pg-data-only-v1",
    "role": "guarded-audit-role",
    "scope": "all-data",
    "canonicalization": "pg-plain-restrict-token-only",
}
REDIS_POLICY = {
    "version": "phase3-redis-canonical-v1",
    "scope": "all-keys-and-absolute-expiry",
    "legacy_runtime_exclusion": "flask-limiter-login-methods-only",
}
LEGACY_VOLUME_POLICY = {
    "version": "phase3-app-volume-v1",
    "scope": "all-directory-file-symlink-content-and-identity-metadata",
    "exclusion": "logs/app.log.[1-10]-regular-files-only",
}
JAVA_VOLUME_POLICY = {
    "version": "phase3-app-volume-v1",
    "scope": "all-directory-file-symlink-content-and-identity-metadata",
    "exclusion": "none",
}
QUEUE_POLICY = {
    "version": "phase3-external-boundary-v1",
    "configured": False,
    "boundary": "no-queue-endpoint-or-worker-is-configured-in-isolated-topology",
}
OBJECT_STORE_POLICY = {
    "version": "phase3-external-boundary-v1",
    "configured": False,
    "boundary": "no-object-store-endpoint-or-credential-is-configured-in-isolated-topology",
}
EXTERNAL_POLICY = {
    "version": "phase3-external-boundary-v2",
    "configured": False,
    "observation_scope": "configuration-only",
    "boundary": "isolated-runtime-has-no-configured-external-write-sink",
    "runtime_write_count": "not-observed",
}


class AuditError(RuntimeError):
    """A runtime-state sample violated an evidence boundary."""


@dataclass(frozen=True)
class AuditScope:
    environment: str
    side: str
    phase: str
    topology: GuardedTopology
    peer_topology: GuardedTopology


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )


def digest(value: bytes | Mapping[str, Any]) -> str:
    payload = canonical_bytes(value) if isinstance(value, Mapping) else value
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _absolute_private_file(value: str, label: str) -> pathlib.Path:
    require(bool(value), f"{label} is required")
    path = pathlib.Path(value)
    require(path.is_absolute(), f"{label} must be absolute")
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise AuditError(f"{label} is not accessible") from exc
    require(stat.S_ISREG(metadata.st_mode) and not stat.S_ISLNK(metadata.st_mode),
            f"{label} must be a regular non-symlink file")
    require(metadata.st_uid == os.getuid() and stat.S_IMODE(metadata.st_mode) == 0o600,
            f"{label} must be owner-only mode 0600")
    return path


def resolve_scope(environment: Mapping[str, str] | None = None) -> AuditScope:
    values = os.environ if environment is None else environment
    requested_environment = values.get("TI_READ_COMPARE_ENVIRONMENT", "")
    side = values.get("TI_READ_COMPARE_SIDE", "")
    phase = values.get("TI_READ_COMPARE_PHASE", "")
    require(requested_environment in {"local", "test"}, "local/test environment is required")
    require(side in SIDE_ENV_FILES, "legacy/java side is required")
    require(phase in ALLOWED_PHASES, "before/after phase is required")

    paths = {
        candidate: _absolute_private_file(values.get(variable, ""), variable)
        for candidate, variable in SIDE_ENV_FILES.items()
    }
    require(paths["legacy"] != paths["java"], "legacy and Java must use different guarded runs")
    topologies = {candidate: guard_env_file(path) for candidate, path in paths.items()}
    require(topologies["legacy"].project != topologies["java"].project,
            "legacy and Java guarded projects must differ")
    require(topologies["legacy"].run_id != topologies["java"].run_id,
            "legacy and Java guarded run ids must differ")
    require(all(topology.environment == requested_environment for topology in topologies.values()),
            "READ_COMPARE environment does not match guarded runs")

    legacy_values = topologies["legacy"].values
    java_values = topologies["java"].values
    selected_resources = (
        legacy_values["TI_PHASE3_LEGACY_DB_NAME"],
        legacy_values["TI_PHASE3_LEGACY_PG_VOLUME"],
        legacy_values["TI_PHASE3_LEGACY_REDIS_VOLUME"],
        legacy_values["TI_PHASE3_LEGACY_APP_VOLUME"],
        java_values["TI_PHASE3_JAVA_DB_NAME"],
        java_values["TI_PHASE3_JAVA_PG_VOLUME"],
        java_values["TI_PHASE3_JAVA_REDIS_VOLUME"],
        java_values["TI_PHASE3_JAVA_APP_VOLUME"],
    )
    require(len(set(selected_resources)) == len(selected_resources),
            "selected legacy/Java resources are not independent")
    selected_ports = (
        legacy_values["TI_PHASE3_LEGACY_API_PORT"],
        legacy_values["TI_PHASE3_LEGACY_POSTGRES_PORT"],
        legacy_values["TI_PHASE3_LEGACY_REDIS_PORT"],
        java_values["TI_PHASE3_JAVA_API_PORT"],
        java_values["TI_PHASE3_JAVA_POSTGRES_PORT"],
        java_values["TI_PHASE3_JAVA_REDIS_PORT"],
    )
    require(len(set(selected_ports)) == len(selected_ports),
            "selected legacy/Java host ports are not independent")
    legacy_artifact = legacy_values["TI_PHASE3_LEGACY_IMAGE"].rsplit("sha256:", 1)[1]
    java_artifact = java_values["TI_PHASE3_JAVA_IMAGE"].rsplit("sha256:", 1)[1]
    require(legacy_artifact != java_artifact,
            "selected legacy/Java application images must differ")
    return AuditScope(
        environment=requested_environment,
        side=side,
        phase=phase,
        topology=topologies[side],
        peer_topology=topologies["java" if side == "legacy" else "legacy"],
    )


def side_value(topology: GuardedTopology, side: str, suffix: str) -> str:
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return topology.values[f"{prefix}_{suffix}"]


def _json_output(raw: bytes, label: str) -> Any:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise AuditError(f"{label} returned invalid JSON") from exc
    return value


def _inspect_json(runner: DockerRunner, container_id: str, template: str, label: str) -> Any:
    require(CONTAINER_ID.fullmatch(container_id) is not None, "invalid container identity")
    result = runner.docker(
        ["container", "inspect", "--format", template, container_id], capture=True
    )
    return _json_output(result.stdout, label)


def _environment_map(value: Any, label: str) -> dict[str, str]:
    require(value is None or isinstance(value, list), f"{label} is invalid")
    result: dict[str, str] = {}
    for entry in value or []:
        require(isinstance(entry, str) and "=" in entry and "\x00" not in entry,
                f"{label} is invalid")
        name, content = entry.split("=", 1)
        require(ENVIRONMENT_NAME.fullmatch(name) is not None and name not in result,
                f"{label} is invalid")
        result[name] = content
    return result


def _image_environment(runner: DockerRunner, image: str, service: str) -> dict[str, str]:
    result = runner.docker(
        ["image", "inspect", "--format", "{{json .Config.Env}}", image], capture=True
    )
    return _environment_map(_json_output(result.stdout, "image environment"),
                            f"{service} image environment")


def _expected_compose_environment(
    topology: GuardedTopology, side: str, kind: str
) -> dict[str, str]:
    value = lambda suffix: side_value(topology, side, suffix)
    if kind == "postgres":
        return {
            "POSTGRES_DB": value("DB_NAME"),
            "POSTGRES_USER": value("DB_OWNER"),
            "POSTGRES_PASSWORD_FILE": "/run/secrets/db.owner.password",
            "TI_PHASE3_DB_APP_USER": value("DB_APP"),
            "TI_PHASE3_DB_AUDIT_USER": value("DB_AUDIT"),
        }
    if kind == "redis":
        return {}
    require(kind == "api", "unknown runtime service kind")
    if side == "legacy":
        return {
            "FLASK_APP": "run.py",
            "FLASK_ENV": "development",
            "FLASK_DEBUG": "0",
            "DATA_DIR": "/data",
            "TI_PHASE3_DB_HOST": "legacy-postgres",
            "TI_PHASE3_DB_NAME": value("DB_NAME"),
            "TI_PHASE3_DB_USER": value("DB_APP"),
            "TI_PHASE3_DB_PASSWORD_FILE": "/run/secrets/db.app.password",
            "TI_PHASE3_REDIS_HOST": "legacy-redis",
            "TI_PHASE3_REDIS_PASSWORD_FILE": "/run/secrets/redis.password",
            "TI_PHASE3_FLASK_SECRET_FILE": "/run/secrets/flask.secret",
            "RATELIMIT_STORAGE_URI": "redis://legacy-redis:6379/0",
            "SSE_ENABLED": "false",
            "PROXY_FIX_ENABLED": "false",
            "MAIL_ENABLED": "false",
            "MAIL_CONSOLE_OUTPUT": "false",
            "SMS_ENABLED": "false",
            "SMS_CONSOLE_OUTPUT": "false",
            "WECHAT_APPID": "",
            "WECHAT_SECRET": "",
            "AI_PROVIDER": "",
            "AI_API_KEY": "",
            "OPENAI_API_KEY": "",
            "DASHSCOPE_API_KEY": "",
        }
    return {
        "SPRING_PROFILES_ACTIVE": "local",
        "TI_SERVER_ADDRESS": "0.0.0.0",
        "TI_SERVER_PORT": "8080",
        "TI_DB_URL": f"jdbc:postgresql://java-postgres:5432/{value('DB_NAME')}",
        "TI_DB_USERNAME": value("DB_APP"),
        "TI_PHASE3_DB_PASSWORD_FILE": "/run/secrets/ti.db.password",
        "TI_REDIS_HOST": "java-redis",
        "TI_REDIS_PORT": "6379",
        "TI_PHASE3_REDIS_PASSWORD_FILE": "/run/secrets/ti.redis.password",
        "TI_SESSION_REDIS_NAMESPACE": value("SESSION_NAMESPACE"),
        "TI_SECURITY_SESSION_COOKIE_NAME": "ti_phase3_java_session",
        "TI_SECURITY_SESSION_CSRF_COOKIE_NAME": "ti_phase3_java_csrf",
        "TI_SECURITY_SESSION_SECURE_COOKIE": "false",
        "TI_MANAGEMENT_ADDRESS": "0.0.0.0",
        "TI_MANAGEMENT_PORT": "9090",
    }


def _expected_mounts(
    topology: GuardedTopology, side: str, kind: str
) -> list[tuple[str, str, str, bool]]:
    value = lambda suffix: side_value(topology, side, suffix)

    def source(relative: str) -> str:
        return str((SCRIPT_DIR / relative).resolve(strict=True))

    def secret(suffix: str) -> str:
        return str(pathlib.Path(value(suffix)).resolve(strict=True))

    if kind == "postgres":
        return [
            ("volume", value("PG_VOLUME"), "/var/lib/postgresql", True),
            ("bind", source("postgres/010-bootstrap-roles.sh"),
             "/docker-entrypoint-initdb.d/010-bootstrap-roles.sh", False),
            ("bind", source("postgres/grant-after-restore.sql"),
             "/usr/local/share/grant-after-restore.sql", False),
            ("bind", secret("DB_OWNER_SECRET_FILE"), "/run/secrets/db.owner.password", False),
            ("bind", secret("DB_APP_SECRET_FILE"), "/run/secrets/db.app.password", False),
            ("bind", secret("DB_AUDIT_SECRET_FILE"), "/run/secrets/db.audit.password", False),
        ]
    if kind == "redis":
        return [
            ("volume", value("REDIS_VOLUME"), "/data", True),
            ("bind", source("runtime/redis-entrypoint.sh"),
             "/phase3/redis-entrypoint.sh", False),
            ("bind", secret("REDIS_SECRET_FILE"), "/run/secrets/redis.password", False),
        ]
    require(kind == "api", "unknown runtime service kind")
    if side == "legacy":
        return [
            ("volume", value("APP_VOLUME"), "/data", True),
            ("bind", source("runtime/legacy-entrypoint.sh"),
             "/phase3/legacy-entrypoint.sh", False),
            ("bind", secret("DB_APP_SECRET_FILE"), "/run/secrets/db.app.password", False),
            ("bind", secret("REDIS_SECRET_FILE"), "/run/secrets/redis.password", False),
            ("bind", secret("FLASK_SECRET_FILE"), "/run/secrets/flask.secret", False),
        ]
    return [
        ("volume", value("APP_VOLUME"), "/app/data", True),
        ("bind", source("runtime/java-entrypoint.sh"), "/phase3/java-entrypoint.sh", False),
        ("bind", secret("DB_APP_SECRET_FILE"), "/run/secrets/ti.db.password", False),
        ("bind", secret("REDIS_SECRET_FILE"), "/run/secrets/ti.redis.password", False),
    ]


def _mount_identities(value: Any, service: str) -> list[tuple[str, str, str, bool]]:
    require(isinstance(value, list), f"{service} mounts are invalid")
    result: list[tuple[str, str, str, bool]] = []
    for mount in value:
        require(isinstance(mount, dict), f"{service} mounts are invalid")
        kind = mount.get("Type")
        destination = mount.get("Destination")
        writable = mount.get("RW")
        require(kind in {"bind", "volume"} and isinstance(destination, str)
                and destination.startswith("/") and type(writable) is bool,
                f"{service} mounts are invalid")
        identity = mount.get("Source") if kind == "bind" else mount.get("Name")
        require(isinstance(identity, str) and identity,
                f"{service} mounts are invalid")
        result.append((kind, identity, destination, writable))
    require(len(result) == len(set(result))
            and len({item[2] for item in result}) == len(result),
            f"{service} mounts are duplicated")
    return result


def _mount_allowlist_matches(
    actual: list[tuple[str, str, str, bool]],
    expected: list[tuple[str, str, str, bool]],
) -> bool:
    if len(actual) != len(expected):
        return False
    expected_by_destination = {item[2]: item for item in expected}
    if len(expected_by_destination) != len(expected):
        return False
    for actual_kind, actual_identity, destination, actual_writable in actual:
        expected_mount = expected_by_destination.get(destination)
        if expected_mount is None:
            return False
        expected_kind, expected_identity, _, expected_writable = expected_mount
        if actual_kind != expected_kind or actual_writable is not expected_writable:
            return False
        allowed_identities = {expected_identity}
        if expected_kind == "bind" and expected_identity.startswith("/"):
            allowed_identities.add("/host_mnt" + expected_identity)
        if actual_identity not in allowed_identities:
            return False
    return True


def _expected_tmpfs(kind: str) -> frozenset[str]:
    if kind == "postgres":
        return frozenset({"/tmp", "/var/run/postgresql"})
    require(kind in {"api", "redis"}, "unknown runtime service kind")
    return frozenset({"/tmp"})


def _validate_tmpfs(value: Any, service: str, kind: str) -> None:
    require(isinstance(value, dict) and set(value) == _expected_tmpfs(kind),
            f"{service} tmpfs mount set mismatch")
    for options in value.values():
        require(isinstance(options, str)
                and {"rw", "noexec", "nosuid"}.issubset(set(options.split(","))),
                f"{service} tmpfs hardening mismatch")


def _expected_networks(topology: GuardedTopology, side: str) -> dict[str, tuple[str, bool]]:
    return {
        f"{topology.project}-{side}-backend": (f"{side}_backend", True),
        f"{topology.project}-{side}-host-access": (f"{side}_host_access", False),
    }


def _validate_networks(
    runner: DockerRunner,
    topology: GuardedTopology,
    side: str,
    expected_container_ids: frozenset[str],
) -> dict[str, str]:
    identities: dict[str, str] = {}
    for name, (logical_name, internal) in _expected_networks(topology, side).items():
        result = runner.docker(
            ["network", "inspect", "--format", "{{json .}}", name], capture=True
        )
        document = _json_output(result.stdout, "network identity")
        require(isinstance(document, dict) and document.get("Name") == name
                and document.get("Internal") is internal,
                f"{side} network identity or Internal policy mismatch")
        identity = document.get("Id")
        require(isinstance(identity, str) and CONTAINER_ID.fullmatch(identity) is not None,
                f"{side} network identity is invalid")
        labels = document.get("Labels")
        require(isinstance(labels, dict)
                and labels.get("com.docker.compose.project") == topology.project
                and labels.get("com.docker.compose.network") == logical_name,
                f"{side} network Compose labels mismatch")
        members = document.get("Containers")
        require(isinstance(members, dict) and set(members) == set(expected_container_ids),
                f"{side} network member set mismatch")
        identities[name] = identity
    return identities


def _validate_container_networks(
    value: Any, service: str, expected_networks: Mapping[str, str]
) -> None:
    require(isinstance(value, dict) and set(value) == set(expected_networks),
            f"{service} network set mismatch")
    for name, expected_identity in expected_networks.items():
        endpoint = value[name]
        require(isinstance(endpoint, dict)
                and endpoint.get("NetworkID") == expected_identity,
                f"{service} network identity mismatch")


def _expected_published_port(topology: GuardedTopology, side: str, kind: str) -> tuple[str, str]:
    if kind == "api":
        return ("8000/tcp" if side == "legacy" else "8080/tcp", side_value(
            topology, side, "API_PORT"))
    if kind == "postgres":
        return "5432/tcp", side_value(topology, side, "POSTGRES_PORT")
    require(kind == "redis", "unknown runtime service kind")
    return "6379/tcp", side_value(topology, side, "REDIS_PORT")


def _validate_published_ports(
    value: Any, service: str, expected_container_port: str, expected_host_port: str
) -> None:
    require(isinstance(value, dict), f"{service} published ports are invalid")
    published: dict[str, Any] = {}
    for container_port, bindings in value.items():
        require(isinstance(container_port, str)
                and CONTAINER_PORT.fullmatch(container_port) is not None,
                f"{service} published ports are invalid")
        if bindings is not None:
            published[container_port] = bindings
    expected = {
        expected_container_port: [{"HostIp": "127.0.0.1", "HostPort": expected_host_port}]
    }
    require(published == expected, f"{service} loopback published port mismatch")


def _validate_container(
    runner: DockerRunner,
    topology: GuardedTopology,
    side: str,
    kind: str,
    service: str,
    container_id: str,
    expected_image: str,
    expected_networks: Mapping[str, str],
) -> tuple[str, str]:
    expected_image_id = runner.image_id(expected_image)
    actual_image_id = runner.container_image_id(container_id)
    require(actual_image_id == expected_image_id, f"{service} image identity mismatch")

    labels = _inspect_json(runner, container_id, "{{json .Config.Labels}}", "container labels")
    require(isinstance(labels, dict), f"{service} labels are invalid")
    require(labels.get("com.docker.compose.project") == topology.project,
            f"{service} project label mismatch")
    require(labels.get("com.docker.compose.service") == service,
            f"{service} service label mismatch")
    require(labels.get("com.docker.compose.oneoff") == "False",
            f"{service} one-off container is forbidden")

    state = _inspect_json(runner, container_id, "{{json .State}}", "container state")
    require(isinstance(state, dict) and state.get("Running") is True
            and state.get("Status") == "running", f"{service} is not running")
    health = state.get("Health")
    require(isinstance(health, dict) and health.get("Status") == "healthy",
            f"{service} is not healthy")

    mounts = _inspect_json(runner, container_id, "{{json .Mounts}}", "container mounts")
    actual_mounts = _mount_identities(mounts, service)
    expected_mounts = _expected_mounts(topology, side, kind)
    require(_mount_allowlist_matches(actual_mounts, expected_mounts),
            f"{service} exact mount allowlist mismatch")
    _validate_tmpfs(
        _inspect_json(runner, container_id, "{{json .HostConfig.Tmpfs}}", "container tmpfs"),
        service,
        kind,
    )
    _validate_container_networks(
        _inspect_json(runner, container_id, "{{json .NetworkSettings.Networks}}",
                      "container networks"),
        service,
        expected_networks,
    )
    container_port, host_port = _expected_published_port(topology, side, kind)
    _validate_published_ports(
        _inspect_json(runner, container_id, "{{json .NetworkSettings.Ports}}",
                      "container published ports"),
        service,
        container_port,
        host_port,
    )
    expected_environment = _image_environment(runner, expected_image, service)
    expected_environment.update(_expected_compose_environment(topology, side, kind))
    actual_environment = _environment_map(
        _inspect_json(runner, container_id, "{{json .Config.Env}}", "container environment"),
        f"{service} effective environment",
    )
    require(actual_environment == expected_environment,
            f"{service} effective environment mismatch")
    return container_id, actual_image_id


def validate_runtime(scope: AuditScope, runner: DockerRunner) -> Mapping[str, Any]:
    side = scope.side
    topology = scope.topology
    services = {
        "api": f"{side}-api",
        "postgres": f"{side}-postgres",
        "redis": f"{side}-redis",
    }
    expected = {"api": side_value(topology, side, "IMAGE"),
                "postgres": POSTGRES_IMAGE, "redis": REDIS_IMAGE}
    container_ids: dict[str, str] = {}
    for kind, service in services.items():
        all_ids = runner.compose_ids(service, running_only=False)
        running_ids = runner.compose_ids(service, running_only=True)
        require(len(all_ids) == 1 and running_ids == all_ids,
                f"{service} must have exactly one running instance")
        container_ids[kind] = all_ids[0]
    network_ids = _validate_networks(
        runner, topology, side, frozenset(container_ids.values())
    )
    image_ids: dict[str, str] = {}
    for kind, service in services.items():
        _, image_ids[kind] = _validate_container(
            runner, topology, side, kind, service, container_ids[kind], expected[kind], network_ids
        )
    configuration_policy = {
        "version": "phase3-runtime-configuration-v1",
        "side": side,
        "networks": _expected_networks(topology, side),
        "published_ports": {
            kind: _expected_published_port(topology, side, kind) for kind in services
        },
        "mounts": {
            kind: _expected_mounts(topology, side, kind) for kind in services
        },
        "tmpfs": {kind: sorted(_expected_tmpfs(kind)) for kind in services},
        "compose_environment": {
            kind: _expected_compose_environment(topology, side, kind) for kind in services
        },
    }
    runtime_identity = {
        "project_sha256": digest(topology.project.encode("utf-8")),
        "api_image_sha256": image_ids["api"],
        "postgres_image_sha256": image_ids["postgres"],
        "redis_image_sha256": image_ids["redis"],
        "configuration_policy_sha256": digest(configuration_policy),
    }
    require(all(SHA256.fullmatch(value) is not None for value in runtime_identity.values()),
            "runtime identity digest is invalid")
    return {
        "api_instances": 1,
        "postgres_instances": 1,
        "redis_instances": 1,
        "identity_sha256": digest(runtime_identity),
        "all_instances_healthy": True,
    }


PG_ROLE_CHECK_SHELL = r'''set -eu
export PGPASSWORD="$(cat /run/secrets/db.audit.password)"
exec psql --no-psqlrc --quiet --tuples-only --no-align --field-separator='|' \
  --username "$1" --dbname "$2" \
  --command="SELECT current_setting('default_transaction_read_only'), current_user = '$1'"
'''

PG_DUMP_SHELL = r'''set -eu
export PGPASSWORD="$(cat /run/secrets/db.audit.password)"
exec pg_dump --dbname="$2" --username="$1" --data-only --no-owner --no-acl \
  --encoding=UTF8 --quote-all-identifiers --no-sync --format=plain
'''


def collect_database(scope: AuditScope, runner: DockerRunner) -> Mapping[str, Any]:
    service = f"{scope.side}-postgres"
    audit_role = side_value(scope.topology, scope.side, "DB_AUDIT")
    database = side_value(scope.topology, scope.side, "DB_NAME")
    role_check = runner.compose(
        ["exec", "-T", service, "sh", "-ec", PG_ROLE_CHECK_SHELL,
         "phase3-audit-role-check", audit_role, database],
        capture=True,
    ).stdout.decode("ascii", "strict").strip()
    require(role_check == "on|t", "PostgreSQL audit role is not read-only")
    data_sha256 = runner.stream_sha256(
        ["exec", "-T", service, "sh", "-ec", PG_DUMP_SHELL,
         "phase3-audit-data", audit_role, database],
        normalize_pg_restore_sql=True,
    )
    require(SHA256.fullmatch(data_sha256) is not None, "PostgreSQL data digest is invalid")
    return {
        "normalized_data_sha256": data_sha256,
        "canonicalization_policy_sha256": digest(PG_DATA_POLICY),
        "audit_role_read_only": True,
    }


REDIS_AUDIT_LUA = r'''
local function fail()
  error('phase3 redis evidence rejected')
end

local function is_private_ipv4(value)
  local a,b,c,d = string.match(value, '^(%d+)%.(%d+)%.(%d+)%.(%d+)$')
  if not a then return false end
  a,b,c,d = tonumber(a),tonumber(b),tonumber(c),tonumber(d)
  if a > 255 or b > 255 or c > 255 or d > 255 then return false end
  return a == 10 or a == 127 or (a == 192 and b == 168) or (a == 172 and b >= 16 and b <= 31)
end

local limit_marker = '/auth.auth_api.api_auth_login_methods/'
local limit_prefix = 'LIMITS:LIMITER/ip:'
local approved = {
  ['5000/1/day'] = {5000, 86400000},
  ['500/1/hour'] = {500, 3600000},
  ['10/1/second'] = {10, 1000}
}

local function excluded_legacy_limiter(key)
  if ARGV[1] ~= 'legacy' or string.sub(key, 1, string.len(limit_prefix)) ~= limit_prefix then
    return false
  end
  local body = string.sub(key, string.len(limit_prefix) + 1)
  local marker_at = string.find(body, limit_marker, 1, true)
  if not marker_at then return false end
  local client = string.sub(body, 1, marker_at - 1)
  local suffix = string.sub(body, marker_at + string.len(limit_marker))
  local rule = approved[suffix]
  if not rule or not is_private_ipv4(client) then fail() end
  local kind = redis.call('TYPE', key).ok
  local value = redis.call('GET', key)
  local ttl = redis.call('PTTL', key)
  if kind ~= 'string' or not value or not string.match(value, '^[1-9]%d*$') then fail() end
  local number = tonumber(value)
  if not number or number > rule[1] or ttl <= 0 or ttl > rule[2] then fail() end
  return true
end

local function encode(value)
  if type(value) == 'string' then return 's' .. string.len(value) .. ':' .. value end
  if type(value) ~= 'table' then fail() end
  local parts = {'a', tostring(#value), ':'}
  for i = 1,#value do parts[#parts + 1] = encode(value[i]) end
  return table.concat(parts)
end

local function payload(key, kind)
  if kind == 'string' then return redis.sha1hex(encode(redis.call('GET', key))) end
  if kind == 'list' then return redis.sha1hex(encode(redis.call('LRANGE', key, 0, -1))) end
  if kind == 'stream' then return redis.sha1hex(encode(redis.call('XRANGE', key, '-', '+'))) end
  if kind == 'set' then
    local values = redis.call('SMEMBERS', key)
    for i = 1,#values do values[i] = redis.sha1hex(values[i]) end
    table.sort(values)
    return redis.sha1hex(table.concat(values, ','))
  end
  if kind == 'zset' then
    local values = redis.call('ZRANGE', key, 0, -1, 'WITHSCORES')
    local rows = {}
    for i = 1,#values,2 do rows[#rows + 1] = redis.sha1hex(values[i]) .. ':' .. values[i + 1] end
    return redis.sha1hex(table.concat(rows, ','))
  end
  if kind == 'hash' then
    local values = redis.call('HGETALL', key)
    local rows = {}
    for i = 1,#values,2 do
      rows[#rows + 1] = redis.sha1hex(values[i]) .. ':' .. redis.sha1hex(values[i + 1])
    end
    table.sort(rows)
    return redis.sha1hex(table.concat(rows, ','))
  end
  fail()
end

local cursor = '0'
local rows = {}
local excluded = 0
repeat
  local result = redis.call('SCAN', cursor, 'COUNT', 1000)
  cursor = result[1]
  for _,key in ipairs(result[2]) do
    if excluded_legacy_limiter(key) then
      excluded = excluded + 1
    else
      local kind = redis.call('TYPE', key).ok
      local expiry = redis.call('PEXPIRETIME', key)
      if expiry == -2 or (expiry ~= -1 and expiry <= 0) then fail() end
      rows[#rows + 1] = redis.sha1hex(key) .. '|' .. kind .. '|' .. tostring(expiry)
        .. '|' .. payload(key, kind)
    end
  end
until cursor == '0'
if excluded > 3 then fail() end
table.sort(rows)
return 'phase3-redis-audit-v1\nexcluded_runtime_key_count=' .. tostring(excluded)
  .. '\nincluded_key_count=' .. tostring(#rows) .. '\n' .. table.concat(rows, '\n')
'''

REDIS_AUDIT_SHELL = r'''set -eu
export REDISCLI_AUTH="$(cat /run/secrets/redis.password)"
exec redis-cli --no-auth-warning --raw EVAL "$1" 0 "$2"
'''


def parse_redis_audit(raw: bytes) -> tuple[str, int, int]:
    try:
        text = raw.decode("ascii").rstrip("\n")
    except UnicodeDecodeError as exc:
        raise AuditError("Redis auditor returned non-ASCII output") from exc
    lines = text.split("\n")
    require(len(lines) >= 3 and lines[0] == "phase3-redis-audit-v1",
            "Redis auditor output version mismatch")
    require(re.fullmatch(r"excluded_runtime_key_count=[0-3]", lines[1]) is not None,
            "Redis exclusion count is invalid")
    require(re.fullmatch(r"included_key_count=(0|[1-9][0-9]{0,8})", lines[2]) is not None,
            "Redis included count is invalid")
    excluded = int(lines[1].split("=", 1)[1])
    included = int(lines[2].split("=", 1)[1])
    rows = lines[3:] if len(lines) > 3 and lines[3] else []
    require(len(rows) == included and all(REDIS_ROW.fullmatch(row) for row in rows),
            "Redis canonical rows are invalid")
    require(rows == sorted(rows) and len(rows) == len(set(rows)),
            "Redis canonical rows are not uniquely sorted")
    canonical = ("\n".join(rows) + "\n").encode("ascii")
    return digest(canonical), excluded, included


def collect_redis(scope: AuditScope, runner: DockerRunner) -> Mapping[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ti-phase3-redis-audit-") as directory:
        output = pathlib.Path(directory) / "canonical.txt"
        runner.compose(
            ["exec", "-T", f"{scope.side}-redis", "sh", "-ec", REDIS_AUDIT_SHELL,
             "phase3-redis-audit", REDIS_AUDIT_LUA, scope.side],
            stdout_path=output,
        )
        metadata = output.stat()
        require(stat.S_ISREG(metadata.st_mode) and metadata.st_size <= 256 * 1024 * 1024,
                "Redis canonical output exceeds the evidence bound")
        content_sha256, excluded, included = parse_redis_audit(output.read_bytes())
    return {
        "normalized_content_sha256": content_sha256,
        "exclusion_policy_sha256": digest(REDIS_POLICY),
        "excluded_runtime_key_count": excluded,
        "included_key_count": included,
    }


VOLUME_AUDIT_PYTHON = r'''
import hashlib, json, os, pathlib, stat

root = pathlib.Path('/audit')
side = os.environ['TI_PHASE3_AUDIT_SIDE']
digest = hashlib.sha256(b'phase3-app-volume-canonical-v1\0')
entry_count = 0
excluded = 0

def frame(value):
    digest.update(len(value).to_bytes(8, 'big'))
    digest.update(value)

def is_excluded(relative, metadata):
    if side != 'legacy' or not stat.S_ISREG(metadata.st_mode): return False
    parts = relative.parts
    if len(parts) != 2 or parts[0] != 'logs': return False
    name = parts[1]
    if not name.startswith('app.log.'): return False
    suffix = name[len('app.log.'):]
    return suffix in {str(value) for value in range(1, 11)}

def visit(directory, relative):
    global entry_count, excluded
    before = sorted(list(os.scandir(directory)), key=lambda entry: os.fsencode(entry.name))
    for entry in before:
        child_relative = relative / entry.name
        metadata = entry.stat(follow_symlinks=False)
        if is_excluded(child_relative, metadata):
            excluded += 1
            continue
        path_bytes = os.fsencode(child_relative.as_posix())
        common = (str(stat.S_IMODE(metadata.st_mode)) + ':' + str(metadata.st_uid)
                  + ':' + str(metadata.st_gid)).encode('ascii')
        if stat.S_ISDIR(metadata.st_mode):
            kind = b'd'
            content = b''
        elif stat.S_ISREG(metadata.st_mode):
            kind = b'f'
            flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
            descriptor = os.open(entry.path, flags)
            try:
                opened = os.fstat(descriptor)
                if (opened.st_ino, opened.st_dev, opened.st_size, opened.st_mtime_ns) != (
                    metadata.st_ino, metadata.st_dev, metadata.st_size, metadata.st_mtime_ns):
                    raise RuntimeError('volume file changed during audit')
                content_digest = hashlib.sha256()
                while True:
                    chunk = os.read(descriptor, 1024 * 1024)
                    if not chunk: break
                    content_digest.update(chunk)
                closed = os.fstat(descriptor)
                if (closed.st_size, closed.st_mtime_ns) != (opened.st_size, opened.st_mtime_ns):
                    raise RuntimeError('volume file changed during audit')
                content = content_digest.digest()
            finally:
                os.close(descriptor)
        elif stat.S_ISLNK(metadata.st_mode):
            kind = b'l'
            content = os.fsencode(os.readlink(entry.path))
        else:
            raise RuntimeError('unsupported application-volume entry type')
        frame(kind); frame(path_bytes); frame(common); frame(content)
        entry_count += 1
        if kind == b'd': visit(pathlib.Path(entry.path), child_relative)
    after = sorted(os.fsencode(entry.name) for entry in os.scandir(directory))
    if after != [os.fsencode(entry.name) for entry in before]:
        raise RuntimeError('volume directory changed during audit')

root_metadata = root.lstat()
if not stat.S_ISDIR(root_metadata.st_mode):
    raise RuntimeError('application volume root is not a directory')
frame(b'd'); frame(b'.')
frame((str(stat.S_IMODE(root_metadata.st_mode)) + ':' + str(root_metadata.st_uid)
       + ':' + str(root_metadata.st_gid)).encode('ascii'))
frame(b'')
entry_count += 1
visit(root, pathlib.PurePath())
print(json.dumps({
    'schema_version': '1',
    'content_sha256': 'sha256:' + digest.hexdigest(),
    'entry_count': entry_count,
    'excluded_rotated_file_count': excluded,
}, sort_keys=True, separators=(',', ':')))
'''


def collect_volume(scope: AuditScope, runner: DockerRunner) -> Mapping[str, Any]:
    volume = side_value(scope.topology, scope.side, "APP_VOLUME")
    helper_image = scope.topology.values["TI_PHASE3_LEGACY_IMAGE"]
    helper_image_id = runner.image_id(helper_image)
    require(SHA256.fullmatch(helper_image_id) is not None, "volume helper image is invalid")
    result = runner.docker(
        [
            "run", "--rm", "--pull", "never", "--network", "none", "--read-only",
            "--cap-drop", "ALL",
            "--security-opt", "no-new-privileges:true", "--pids-limit", "64",
            "--memory", "256m", "--user", "0:0",
            "--env", f"TI_PHASE3_AUDIT_SIDE={scope.side}",
            "--mount", f"type=volume,source={volume},target=/audit,readonly",
            "--entrypoint", "python", helper_image, "-c", VOLUME_AUDIT_PYTHON,
        ],
        capture=True,
    )
    value = _json_output(result.stdout, "application-volume auditor")
    require(isinstance(value, dict) and set(value) == {
        "schema_version", "content_sha256", "entry_count", "excluded_rotated_file_count"
    }, "application-volume auditor fields are invalid")
    require(value["schema_version"] == "1" and SHA256.fullmatch(value["content_sha256"]),
            "application-volume auditor digest is invalid")
    for field in ("entry_count", "excluded_rotated_file_count"):
        require(type(value[field]) is int and 0 <= value[field] <= 10_000_000,
                "application-volume auditor count is invalid")
    if scope.side == "java":
        require(value["excluded_rotated_file_count"] == 0,
                "Java application volume may not exclude files")
    else:
        require(value["excluded_rotated_file_count"] <= 10,
                "legacy rotated-log exclusion count is invalid")
    policy = LEGACY_VOLUME_POLICY if scope.side == "legacy" else JAVA_VOLUME_POLICY
    return {
        "normalized_manifest_sha256": value["content_sha256"],
        "exclusion_policy_sha256": digest(policy),
        "excluded_rotated_file_count": value["excluded_rotated_file_count"],
        "included_entry_count": value["entry_count"],
    }


def collect_state(scope: AuditScope, runner: DockerRunner) -> Mapping[str, Any]:
    runner.preflight_local_context()
    runtime = validate_runtime(scope, runner)
    database = collect_database(scope, runner)
    redis = collect_redis(scope, runner)
    volume = collect_volume(scope, runner)
    return {
        "database": database,
        "redis": redis,
        "volume": volume,
        "queue": {
            "configured": False,
            "boundary_policy_sha256": digest(QUEUE_POLICY),
        },
        "object_store": {
            "configured": False,
            "boundary_policy_sha256": digest(OBJECT_STORE_POLICY),
        },
        "external_writes": {
            "runtime_observation_performed": False,
            "configured_sink": False,
            "boundary_policy_sha256": digest(EXTERNAL_POLICY),
        },
        "external_boundary": {
            "configured": False,
            "observation_scope": "configuration-only",
            "boundary_policy_sha256": digest(EXTERNAL_POLICY),
        },
        "runtime": runtime,
    }


def build_document(scope: AuditScope, state: Mapping[str, Any]) -> Mapping[str, Any]:
    return {
        "schema_version": "1",
        "environment": scope.environment,
        "side": scope.side,
        "phase": scope.phase,
        "auditor": AUDITOR_ID,
        "state": state,
    }


def main() -> int:
    try:
        scope = resolve_scope()
        runner = DockerRunner(scope.topology, {})
        document = build_document(scope, collect_state(scope, runner))
        print(json.dumps(document, ensure_ascii=False, separators=(",", ":"), sort_keys=True))
        return 0
    except (AuditError, GuardError, RehearsalError, OSError, UnicodeError, ValueError) as exc:
        print(f"Phase 3 runtime state auditor rejected input: {exc}", file=os.sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
