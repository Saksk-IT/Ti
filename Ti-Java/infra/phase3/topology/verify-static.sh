#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
COMPOSE_FILE="$SCRIPT_DIR/compose.isolated.yml"
SCHEMA_FILE="$SCRIPT_DIR/snapshot-manifest.schema.json"
TEST_FILE="$SCRIPT_DIR/test_topology.py"
AUDITOR_FILE="$SCRIPT_DIR/runtime_state_auditor.py"
AUDITOR_TEST_FILE="$SCRIPT_DIR/test_runtime_state_auditor.py"
WRITE_CAPTURE_FILE="$SCRIPT_DIR/capture_login_write_evidence.py"
WRITE_CAPTURE_TEST_FILE="$SCRIPT_DIR/test_capture_login_write_evidence.py"

command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 is required" >&2
    exit 1
}
command -v docker >/dev/null 2>&1 || {
    echo "Docker CLI with Compose is required" >&2
    exit 1
}

python3 -m py_compile \
    "$SCRIPT_DIR/topology_guard.py" \
    "$SCRIPT_DIR/prepare_run.py" \
    "$SCRIPT_DIR/snapshot_bundle.py" \
    "$SCRIPT_DIR/rehearse_switch.py" \
    "$AUDITOR_FILE" \
    "$WRITE_CAPTURE_FILE" \
    "$TEST_FILE" \
    "$AUDITOR_TEST_FILE" \
    "$WRITE_CAPTURE_TEST_FILE"

python3 - "$SCRIPT_DIR" "$COMPOSE_FILE" "$SCHEMA_FILE" "$AUDITOR_FILE" \
    "$WRITE_CAPTURE_FILE" <<'PY'
import json
import pathlib
import re
import stat
import sys

script_dir, compose_path, schema_path, auditor_path, write_capture_path = map(
    pathlib.Path, sys.argv[1:]
)
compose_source = compose_path.read_text(encoding="utf-8")
guard_source = (script_dir / "topology_guard.py").read_text(encoding="utf-8")
rehearsal_source = (script_dir / "rehearse_switch.py").read_text(encoding="utf-8")
snapshot_source = (script_dir / "snapshot_bundle.py").read_text(encoding="utf-8")
redis_source = (script_dir / "runtime/redis-entrypoint.sh").read_text(encoding="utf-8")
auditor_source = auditor_path.read_text(encoding="utf-8")
write_capture_source = write_capture_path.read_text(encoding="utf-8")
application_source = (
    script_dir.parent.parent.parent / "server/src/main/resources/application.yml"
).read_text(
    encoding="utf-8"
)
grant_source = (script_dir / "postgres/grant-after-restore.sql").read_text(encoding="utf-8")
schema = json.loads(schema_path.read_text(encoding="utf-8"))


def require(condition, message):
    if not condition:
        raise SystemExit(f"Phase 3 topology static gate failed: {message}")


require("../" not in compose_source, "parent path in Compose")
require("network_mode:" not in compose_source, "network_mode bypass")
require("external: true" not in compose_source, "external network or volume")
require(len(re.findall(r'^\s+- "127\.0\.0\.1:\$\{TI_PHASE3_', compose_source, re.M)) == 6,
        "six loopback-only host bindings")
for marker in (
    "legacy_backend", "java_backend", "legacy_host_access", "java_host_access",
    "legacy_postgres_data", "java_postgres_data", "legacy_redis_data",
    "java_redis_data", "legacy_app_data", "java_app_data",
    "redis-entrypoint.sh", "pull_policy: never", "profiles:", "runtime",
    "db.audit.password", "grant-after-restore.sql", 'MAIL_ENABLED: "false"',
    'SMS_ENABLED: "false"', 'SSE_ENABLED: "false"',
):
    require(marker in compose_source, f"Compose safety marker {marker}")
for marker in (
    "PRODUCTION_FORBIDDEN", "SHARED_VOLUME_FORBIDDEN", "SHARED_DATABASE_FORBIDDEN",
    "PINNED_IMAGE", "fixed ignored Phase 3 topology directory",
):
    require(marker in guard_source, f"guard marker {marker}")
for marker in (
    "STOP_LEGACY_CAPTURE_RESTORE_JAVA", "STOP_JAVA_CAPTURE_RESTORE_LEGACY",
    "REMOTE_DOCKER_FORBIDDEN", "--single-transaction", "--no-owner", "--no-acl",
    "DUAL_WRITE_FORBIDDEN", "target volume must not pre-exist",
    "source_containers_retired_without_deleting_source_volumes",
):
    require(marker in rehearsal_source, f"rehearsal safety marker {marker}")
for marker in (
    "snapshot checksum mismatch", "hard-linked snapshot file is forbidden",
    "snapshot bundle has missing or extra files", "snapshot scope mismatch",
    "fresh-empty-volume", "PGDMP",
):
    require(marker in snapshot_source, f"snapshot safety marker {marker}")
for marker in (
    "TI_PHASE3_AUDIT_LEGACY_ENV_FILE", "TI_PHASE3_AUDIT_JAVA_ENV_FILE",
    "phase3-runtime-state-auditor-v2", "guarded-audit-role",
    "flask-limiter-login-methods-only", "LIMITS:LIMITER/ip:",
    "excluded_runtime_key_count",
    "no-queue-endpoint-or-worker-is-configured", "no-object-store-endpoint-or-credential",
):
    require(marker in auditor_source, f"runtime auditor safety marker {marker}")
for marker in (
    "phase3-login-write-evidence-v1", "phase3-login-private-before-v1",
    "writes_issued_by_collector", "raw_password_hash_persisted",
    "raw_cookie_or_session_id_persisted", "UNKNOWN_REDIS_KEY_OR_TYPE",
    "INVALID_SERVER_SESSION_SEMANTICS", "transition_guard_sha256",
    "database changed outside the sole has_password_set false-to-true transition",
    "first_attempt_counter", "target_session_binding_sha256",
    "application_volume_manifest_sha256",
):
    require(marker in write_capture_source, f"write evidence collector safety marker {marker}")
for forbidden in (
    "expiration_prefix", "SESSION_EXPIRY_MISSING", "SESSION_EXPIRATION_MEMBER_MISSING",
):
    require(forbidden not in write_capture_source,
            f"non-indexed Spring Session collector contains indexed marker {forbidden}")
require("repository-type: default" in application_source,
        "Spring Session repository type must be explicitly non-indexed")
for forbidden in (
    "import urllib", "import requests", "import socket", "http.client", "urlopen(",
    "requests.post", "shell=True",
):
    require(forbidden not in write_capture_source,
            f"write evidence collector HTTP/shell capability {forbidden}")
for marker in (
    "GRANT SELECT ON ALL TABLES IN SCHEMA public TO %I",
    "GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO %I",
    "GRANT SELECT ON TABLES TO %I",
    "GRANT SELECT ON SEQUENCES TO %I",
):
    require(marker in grant_source, f"audit read grant marker {marker}")
require("shell=True" not in guard_source + rehearsal_source + snapshot_source + auditor_source,
        "shell=True is forbidden")
require("maxmemory-policy noeviction" in redis_source, "Redis noeviction policy")
require("compose.prod" not in guard_source + rehearsal_source + snapshot_source + auditor_source,
        "parent production Compose reference")
require("/Users/" not in compose_source + guard_source + rehearsal_source + snapshot_source
        + auditor_source,
        "host-specific absolute path")

require(schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema",
        "snapshot schema draft")
require(schema.get("additionalProperties") is False, "snapshot top-level closure")
require(schema["properties"]["environment"].get("enum") == ["local", "test"],
        "snapshot environment allowlist")
require(schema["properties"]["scope"].get("const") == "phase3-auth-postgresql-only",
        "snapshot limited scope")
require(schema["properties"]["postgres"]["properties"]["server_version_num"].get("const") ==
        "180004", "snapshot pinned PostgreSQL version")
require(schema["properties"]["payload"]["properties"]["canonicalization"].get("const") ==
        "pg-restore-sql-v2-restrict-token-static-ascii-varchar-text-array",
        "snapshot canonicalization version")
require(schema["properties"]["redis_policy"]["properties"]["copied"].get("const") is False,
        "Redis copy prohibition")
require(schema["properties"]["application_volume_policy"]["properties"]["copied"].get("const")
        is False, "application-volume copy prohibition")

for executable in (
    script_dir / "runtime/legacy-entrypoint.sh",
    script_dir / "runtime/java-entrypoint.sh",
    script_dir / "runtime/redis-entrypoint.sh",
    script_dir / "postgres/010-bootstrap-roles.sh",
    script_dir / "verify-data-plane.sh",
    auditor_path,
    write_capture_path,
):
    require(executable.stat().st_mode & stat.S_IXUSR, f"missing executable bit: {executable.name}")
PY

RUN_ID="verify-$$"
ENV_FILE=$(python3 "$SCRIPT_DIR/prepare_run.py" PREPARE \
    --environment test \
    --run-id "$RUN_ID" \
    --legacy-image "legacy@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" \
    --java-image "java@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
RUN_DIR=$(dirname "$ENV_FILE")
TEMP_DIR=$(mktemp -d "${TMPDIR:-/tmp}/ti-phase3-topology.XXXXXX")
cleanup() {
    rm -rf -- "$RUN_DIR" "$TEMP_DIR"
}
trap cleanup EXIT HUP INT TERM

python3 - "$SCRIPT_DIR" "$ENV_FILE" "$COMPOSE_FILE" "$TEMP_DIR/compose.json" <<'PY'
import json
import os
import pathlib
import subprocess
import sys

script_dir, env_file, compose_file, output_file = map(pathlib.Path, sys.argv[1:])
sys.path.insert(0, str(script_dir))
from topology_guard import ENV_KEYS, guard_env_file

topology = guard_env_file(env_file)
environment = dict(os.environ)
for key in ENV_KEYS:
    environment.pop(key, None)
environment.update(topology.values)
command = [
    "docker", "compose", "--env-file", str(env_file), "--file", str(compose_file),
    "--profile", "runtime", "config", "--format", "json",
]
result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        env=environment, check=False)
if result.returncode:
    raise SystemExit("Phase 3 topology static gate failed: docker compose config")
output_file.write_bytes(result.stdout)
config = json.loads(result.stdout)


def require(condition, message):
    if not condition:
        raise SystemExit(f"Phase 3 rendered topology invalid: {message}")


services = config.get("services", {})
require(set(services) == {
    "legacy-api", "legacy-postgres", "legacy-redis",
    "java-api", "java-postgres", "java-redis",
}, "exact service set")


def networks(name):
    value = services[name].get("networks", {})
    return set(value if isinstance(value, dict) else value)


require(networks("legacy-api") == {"legacy_backend", "legacy_host_access"},
        "legacy API networks")
require(networks("legacy-postgres") == {"legacy_backend", "legacy_host_access"},
        "legacy PostgreSQL networks")
require(networks("legacy-redis") == {"legacy_backend", "legacy_host_access"},
        "legacy Redis networks")
require(networks("java-api") == {"java_backend", "java_host_access"}, "Java API networks")
require(networks("java-postgres") == {"java_backend", "java_host_access"},
        "Java PostgreSQL networks")
require(networks("java-redis") == {"java_backend", "java_host_access"},
        "Java Redis networks")
for backend in ("legacy_backend", "java_backend"):
    require(config["networks"][backend].get("internal") is True, f"{backend} internal")

published = []
for service in services.values():
    for port in service.get("ports", []):
        require(port.get("host_ip") == "127.0.0.1", "non-loopback port")
        published.append(int(port["published"]))
require(len(published) == 6 and len(set(published)) == 6, "six distinct ports")

volume_names = [value["name"] for value in config["volumes"].values()]
require(len(volume_names) == 6 and len(set(volume_names)) == 6, "six distinct named volumes")
require(all(name.startswith(topology.project + "-") for name in volume_names),
        "volume project ownership")
for name, service in services.items():
    require(service.get("read_only") is True, f"{name} read-only rootfs")
    require(service.get("cap_drop") == ["ALL"], f"{name} capability drop")
    require("no-new-privileges:true" in service.get("security_opt", []),
            f"{name} no-new-privileges")

legacy_mounts = services["legacy-api"].get("volumes", [])
java_mounts = services["java-api"].get("volumes", [])
legacy_owned_volumes = {
    value["name"] for key, value in config["volumes"].items()
    if key.startswith("legacy_")
}
java_owned_volumes = {
    value["name"] for key, value in config["volumes"].items()
    if key.startswith("java_")
}
legacy_named_mounts = {
    item.get("source") for item in legacy_mounts if item.get("type") == "volume"
}
java_named_mounts = {
    item.get("source") for item in java_mounts if item.get("type") == "volume"
}
require(legacy_named_mounts.isdisjoint(java_owned_volumes),
        "legacy API cannot mount Java volumes")
require(java_named_mounts.isdisjoint(legacy_owned_volumes),
        "Java API cannot mount legacy volumes")
for service in services.values():
    for mount in service.get("volumes", []):
        if mount.get("type") == "bind":
            source = pathlib.Path(mount["source"]).resolve()
            require(source.is_relative_to(script_dir), "bind escaped Phase 3 topology directory")
PY

(
    cd "$TEMP_DIR"
    PYTHONWARNINGS=error python3 "$TEST_FILE"
    PYTHONWARNINGS=error python3 "$AUDITOR_TEST_FILE"
    PYTHONWARNINGS=error python3 "$WRITE_CAPTURE_TEST_FILE"
)

echo "Phase 3 isolated-topology/snapshot/switch gates passed"
