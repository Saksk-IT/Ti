#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TI_JAVA_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
COMPOSE_FILE="$TI_JAVA_DIR/compose.dev.yml"
ENV_FILE="$TI_JAVA_DIR/.env.example"
SCHEMA_FILE="$TI_JAVA_DIR/server/src/test/resources/db/phase2/minimal-reference-schema.sql"
EXPECTED_SCHEMA_SHA=2873948e1d0a59eb8ceb9dce94e23ec05d9db6bfe288e33140d33519dac62c83

sha256_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$1" | awk '{print $1}'
    else
        echo "sha256sum or shasum is required" >&2
        return 1
    fi
}

command -v docker >/dev/null 2>&1 || {
    echo "Docker CLI is required" >&2
    exit 1
}
command -v python3 >/dev/null 2>&1 || {
    echo "Python 3 is required to validate the wormhole JSON evidence" >&2
    exit 1
}

docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" config --quiet
docker compose --env-file "$ENV_FILE" --file "$COMPOSE_FILE" config --format json | \
    python3 -c '
import json
import sys

config = json.load(sys.stdin)

def require(condition, message):
    if not condition:
        raise SystemExit(f"Compose topology invalid: {message}")

services = config.get("services", {})
networks = config.get("networks", {})

def service_networks(name):
    configured = services.get(name, {}).get("networks", {})
    if isinstance(configured, dict):
        return set(configured)
    return set(configured)

def normalized_ports(name):
    normalized = []
    for port in services.get(name, {}).get("ports", []):
        normalized.append({
            "host_ip": port.get("host_ip"),
            "published": str(port.get("published")),
            "target": int(port.get("target")),
            "protocol": port.get("protocol", "tcp"),
        })
    return normalized

require(service_networks("api") == {"backend", "host_access"},
        "api must join backend and host_access")
require(service_networks("postgres") == {"backend", "host_access"},
        "postgres must join backend and host_access")
require(service_networks("redis") == {"backend"},
        "redis must remain backend-only")
require(networks.get("backend", {}).get("internal") is True,
        "backend must be internal")
require(networks.get("host_access", {}).get("internal", False) is False,
        "host_access must be non-internal")
require(normalized_ports("api") == [{
            "host_ip": "127.0.0.1",
            "published": "18080",
            "target": 8080,
            "protocol": "tcp",
        }], "api must publish only 127.0.0.1:18080 to 8080")
require(normalized_ports("postgres") == [{
            "host_ip": "127.0.0.1",
            "published": "25432",
            "target": 5432,
            "protocol": "tcp",
        }], "postgres must publish only 127.0.0.1:25432 to 5432")
require(normalized_ports("redis") == [], "redis must publish no host ports")
require(services.get("api", {}).get("expose") == ["9090"],
        "api management port 9090 must be expose-only")
'

actual_schema_sha=$(sha256_file "$SCHEMA_FILE")
if [ "$actual_schema_sha" != "$EXPECTED_SCHEMA_SHA" ]; then
    echo "Phase 2 schema fixture SHA-256 mismatch" >&2
    exit 1
fi

CONTAINER_IMAGES_FILE="$TI_JAVA_DIR/server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java"
WORMHOLE_FILE="$TI_JAVA_DIR/infra/phase2/verify-local-reference-wormhole.sh"
WORMHOLE_REPORT="$TI_JAVA_DIR/infra/phase2/local-reference-verification.json"
READ_ONLY_INIT="$TI_JAVA_DIR/infra/phase2/postgres/020-create-readonly-role.sh"
REFERENCE_ASSERTIONS="$TI_JAVA_DIR/server/src/test/java/io/saksk/ti/support/ReferenceSchemaAssertions.java"
DRIFT_MANIFEST="$TI_JAVA_DIR/infra/phase2/reference-drift-manifest.json"
BUILD_CONTEXT_HASHER="$TI_JAVA_DIR/infra/phase2/hash-java-build-context.sh"

assert_file_contains() {
    label=$1
    expected=$2
    file=$3
    if ! grep --fixed-strings --quiet -- "$expected" "$file"; then
        echo "$label does not contain its required audited value in $file" >&2
        exit 1
    fi
}

assert_file_contains "Maven build image" \
    "maven:3.9.16-eclipse-temurin-25@sha256:7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c" \
    "$TI_JAVA_DIR/server/Dockerfile"
assert_file_contains "Dockerfile frontend" \
    "docker/dockerfile:1.7@sha256:a57df69d0ea827fb7266491f2813635de6f17269be881f696fbfdf2d83dda33e" \
    "$TI_JAVA_DIR/server/Dockerfile"
assert_file_contains "Temurin runtime image" \
    "eclipse-temurin:25.0.3_9-jre-noble@sha256:2f1da100788559b397bcf48c736169ea5b070bde84e55f203bbee8e83d87a175" \
    "$TI_JAVA_DIR/server/Dockerfile"
assert_file_contains "Fresh Docker package lifecycle" \
    "-Dmaven.test.skip=true clean package" "$TI_JAVA_DIR/server/Dockerfile"
assert_file_contains "Clean default Maven verification" \
    "set -- clean verify" "$TI_JAVA_DIR/infra/phase2/verify-in-maven-container.sh"
assert_file_contains "Executable JAR stale-class gate" \
    "Executable JAR contains forbidden stale ActorId.class" \
    "$TI_JAVA_DIR/infra/phase2/verify-in-maven-container.sh"
assert_file_contains "Compose PostgreSQL 18 image" \
    "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15" \
    "$COMPOSE_FILE"
assert_file_contains "Testcontainers PostgreSQL 18 image" \
    "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15" \
    "$CONTAINER_IMAGES_FILE"
assert_file_contains "Testcontainers PostgreSQL 16 image" \
    "postgres:16.14-alpine@sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777" \
    "$CONTAINER_IMAGES_FILE"
assert_file_contains "Compose Redis image" \
    "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf" \
    "$COMPOSE_FILE"
assert_file_contains "Testcontainers Redis image" \
    "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf" \
    "$CONTAINER_IMAGES_FILE"
assert_file_contains "Wormhole PostgreSQL 18 image" \
    "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15" \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole Redis image" \
    "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf" \
    "$WORMHOLE_FILE"

assert_file_contains "Observed FK delete rule" "ON DELETE SET NULL" "$SCHEMA_FILE"
assert_file_contains "JDBC FK delete-rule assertion" "importedKeySetNull" "$REFERENCE_ASSERTIONS"
assert_file_contains "Read-role TEMP revoke" \
    'REVOKE TEMPORARY ON DATABASE :"db_name" FROM PUBLIC' "$READ_ONLY_INIT"
assert_file_contains "Read-role TEMP ACL assertion" \
    "has_database_privilege(current_user, current_database(), 'TEMPORARY')" \
    "$REFERENCE_ASSERTIONS"
assert_file_contains "Read-role ACL override assertion" \
    "SET default_transaction_read_only = off" "$REFERENCE_ASSERTIONS"

current_dockerfile_sha=$(sha256_file "$TI_JAVA_DIR/server/Dockerfile")
current_build_context_sha=$("$BUILD_CONTEXT_HASHER")
python3 - "$WORMHOLE_REPORT" "$DRIFT_MANIFEST" \
    "$current_dockerfile_sha" "$current_build_context_sha" <<'PY'
import datetime as dt
import json
import pathlib
import re
import sys

report_path, manifest_path, dockerfile_sha, build_context_sha = sys.argv[1:]
with pathlib.Path(report_path).open(encoding="utf-8") as handle:
    report = json.load(handle)
with pathlib.Path(manifest_path).open(encoding="utf-8") as handle:
    manifest = json.load(handle)

def require(condition, message):
    if not condition:
        raise SystemExit(f"Wormhole evidence invalid: {message}")

require(report.get("schemaVersion") == 1, "schemaVersion")
captured_at = report.get("capturedAt")
require(isinstance(captured_at, str), "capturedAt type")
try:
    dt.datetime.fromisoformat(captured_at.replace("Z", "+00:00"))
except ValueError as error:
    raise SystemExit("Wormhole evidence invalid: capturedAt format") from error

observed = manifest["observedReference"]
source = report.get("source", {})
require(source.get("classification") == "explicitly-approved-local-development-reference",
        "source classification")
require(source.get("legacySourceCommit") == manifest.get("legacySourceCommit"),
        "legacy source commit")
require(source.get("alembicHead") == manifest.get("alembicHead"), "Alembic head")
require(source.get("serverVersion") == observed.get("postgresVersion"), "source version")
require(source.get("serverVersionNum") == str(observed.get("postgresVersionNum")),
        "source version num")
require(source.get("publicBaseTables") == observed.get("physicalTableCount"),
        "source table count")
require(source.get("publicColumns") == observed.get("physicalColumnCount"),
        "source column count")

restore = report.get("restore", {})
require(restore.get("image") ==
        "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
        "restore image")
require(restore.get("serverVersion") == observed.get("postgresVersion"), "target version")
require(restore.get("serverVersionNum") == str(observed.get("postgresVersionNum")),
        "target version num")
require(restore.get("publicBaseTables") == observed.get("physicalTableCount"),
        "target table count")
require(restore.get("publicColumns") == observed.get("physicalColumnCount"),
        "target column count")
require(re.fullmatch(r"[0-9a-f]{64}", restore.get("canonicalSchemaDumpSha256", ""))
        is not None, "canonical schema SHA-256")
require(restore.get("schemaDumpPersisted") is False, "schema dump cleanup")

read_role = report.get("readRole", {})
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
require(read_role == expected_read_role, "complete read-role ACL evidence")

java = report.get("java", {})
require(java.get("dockerfileSha256") == dockerfile_sha, "stale Dockerfile evidence")
require(java.get("buildContextSha256") == build_context_sha, "stale Java build-context evidence")
require("imageId" not in java, "environment-specific image ID is forbidden")
require(java.get("hibernateDdlAuto") == "validate", "Hibernate mode")
require(java.get("startupPassed") is True, "Java startup")
require(java.get("readinessPassed") is True, "Java readiness")
require(report.get("productionDatabaseVersion") == "unknown", "production version boundary")
require(report.get("flywayBaselineCreated") is False, "Flyway baseline boundary")

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
require(not any(value.startswith("/") for value in strings), "absolute path leaked")
serialized = json.dumps(report, sort_keys=True).lower()
for forbidden in ("password", "secret", "ti-postgres-1", "studyuser", "ti_db"):
    require(forbidden not in serialized, f"sensitive/source identifier leaked: {forbidden}")
PY

if grep -R --line-number --extended-regexp \
    'disabledWithoutDocker|withReuse|testcontainers\.reuse\.enable' \
    "$TI_JAVA_DIR/server/src/test"
then
    echo "Forbidden Testcontainers skip/reuse setting detected" >&2
    exit 1
fi

echo "Phase 2 static infrastructure checks passed"
