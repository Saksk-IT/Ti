#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TI_JAVA_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
COMPOSE_FILE="$TI_JAVA_DIR/compose.dev.yml"
ENV_FILE="$TI_JAVA_DIR/.env.example"
SCHEMA_FILE="$TI_JAVA_DIR/server/src/test/resources/db/phase2/minimal-reference-schema.sql"
USER_COUNTS_SECRET_EXAMPLE="$TI_JAVA_DIR/infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example"
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
secrets = config.get("secrets", {})

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

api_secrets = services.get("api", {}).get("secrets", [])
require(api_secrets == [
            {"source": "ti_db_password", "target": "ti.db.password"},
            {"source": "ti_redis_password", "target": "ti.redis.password"},
            {
                "source": "ti_login_rate_limit_key_secret",
                "target": "ti.login-rate-limit.key-secret",
            },
            {
                "source": "ti_personal_bank_user_counts_rate_limit_key_secret",
                "target": "ti.personal-bank-user-counts-read-rate-limit.key-secret",
            },
        ], "api must mount the exact database, Redis, login-HMAC, and user-counts HMAC configtree secrets")
user_counts_secret = secrets.get(
        "ti_personal_bank_user_counts_rate_limit_key_secret", {})
user_counts_secret_file = user_counts_secret.get("file")
require(isinstance(user_counts_secret_file, str) and user_counts_secret_file.endswith(
        "/infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example"),
        "user-counts HMAC secret must use the dedicated configtree file boundary")
require("environment" not in user_counts_secret,
        "user-counts HMAC secret must not use an unsupported Compose environment secret")
require("TI_JAVA_PERSONAL_BANK_USER_COUNTS_RATE_LIMIT_KEY_SECRET" not in
        services.get("api", {}).get("environment", {}),
        "user-counts HMAC secret must not be exposed as a container environment variable")

redis_command = services.get("redis", {}).get("command", [])
require(isinstance(redis_command, list), "redis command must render as an argv list")
redis_command_text = " ".join(redis_command)
for directive in (
        "appendonly yes",
        "appendfsync everysec",
        "maxmemory 128mb",
        "maxmemory-policy noeviction",
):
    require(directive in redis_command_text,
            f"redis command must enforce {directive}")
'

actual_schema_sha=$(sha256_file "$SCHEMA_FILE")
if [ "$actual_schema_sha" != "$EXPECTED_SCHEMA_SHA" ]; then
    echo "Phase 2 schema fixture SHA-256 mismatch" >&2
    exit 1
fi

CONTAINER_IMAGES_FILE="$TI_JAVA_DIR/server/src/test/java/io/saksk/ti/support/Phase2ContainerImages.java"
WORMHOLE_FILE="$TI_JAVA_DIR/infra/phase2/verify-local-reference-wormhole.sh"
WORMHOLE_SUCCESSOR_VALIDATOR="$TI_JAVA_DIR/tools/phase2_wormhole_successor_acceptance.py"
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
assert_file_contains "Phase 2 login-HMAC env-file boundary" \
    "TI_JAVA_LOGIN_RATE_LIMIT_KEY_SECRET_FILE=./infra/phase2/secrets/ti-login-rate-limit-key-secret.example" \
    "$ENV_FILE"
assert_file_contains "Phase 2 login-HMAC Compose default" \
    'TI_JAVA_LOGIN_RATE_LIMIT_KEY_SECRET_FILE:-./infra/phase2/secrets/ti-login-rate-limit-key-secret.example' \
    "$COMPOSE_FILE"
assert_file_contains "Phase 2 public login-HMAC placeholder" \
    "PUBLIC-TEST-ONLY-phase2-login-rate-hmac-key-0001" \
    "$TI_JAVA_DIR/infra/phase2/secrets/ti-login-rate-limit-key-secret.example"
assert_file_contains "Phase 4C user-counts HMAC env-file boundary" \
    "TI_JAVA_PERSONAL_BANK_USER_COUNTS_RATE_LIMIT_KEY_SECRET_FILE=./infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example" \
    "$ENV_FILE"
assert_file_contains "Phase 4C user-counts HMAC Compose file source" \
    'TI_JAVA_PERSONAL_BANK_USER_COUNTS_RATE_LIMIT_KEY_SECRET_FILE:-./infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example' \
    "$COMPOSE_FILE"
assert_file_contains "Phase 4C public user-counts HMAC placeholder" \
    "PUBLIC-TEST-ONLY-phase4c-user-counts-rate-hmac-key-0001" \
    "$USER_COUNTS_SECRET_EXAMPLE"
if cmp -s \
    "$TI_JAVA_DIR/infra/phase2/secrets/ti-login-rate-limit-key-secret.example" \
    "$USER_COUNTS_SECRET_EXAMPLE"; then
    echo "Login and user-counts HMAC example secrets must remain distinct" >&2
    exit 1
fi
assert_file_contains "Wormhole PostgreSQL 18 image" \
    "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15" \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole Redis image" \
    "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf" \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole ephemeral login-HMAC secret" \
    'login_rate_limit_key_secret="phase2-$(od -An -N32 -tx1 /dev/urandom' \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole login-HMAC configtree mount" \
    'target=/run/secrets/ti.login-rate-limit.key-secret,readonly' \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole ephemeral user-counts HMAC secret" \
    'user_counts_rate_limit_key_secret="phase2-$(od -An -N32 -tx1 /dev/urandom' \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole user-counts HMAC configtree mount" \
    'target=/run/secrets/ti.personal-bank-user-counts-read-rate-limit.key-secret,readonly' \
    "$WORMHOLE_FILE"
assert_file_contains "Wormhole explicit versioned report" \
    '--report is required and must name a new versioned evidence file' \
    "$WORMHOLE_FILE"
assert_file_contains "Fixed historical WORM trust root" \
    '779154127fc700e213fbb3d5f83c112c090d3481236dcd361dbd72b74a0bd1ad' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C WORM successor" \
    'cfb262319ded0840218fd9bfb4deff1e7bc9c66b5849e3ff05f49a459e686884' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C read WORM successor" \
    'fade745bfa0da6ea7d4fc6a16dcee499149ee06dc1113fc92b5256df23cc42e9' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C read-access WORM successor" \
    'a393e79afb76c53a1aca8be1e4709506b58ad062e3c6536c26c12f10b29d1ec6' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP implementation WORM successor" \
    '7b863dd3b3bc94cbbfbd623d39495fed01c45dcb816598a759474d4372fbca39' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP implementation WORM predecessor" \
    'predecessor_sha256=PHASE4C_READ_ACCESS_REPORT_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight WORM successor" \
    '283d63d5b38b20dfdae01ff237e407d593ce711e9f9af35f7c666210312edd72' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight Java build-context" \
    '2b2f2b9956a9188a81606b50405ac82ded0253bbe2539d6fb841575b4c21dcf9' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight WORM predecessor" \
    'predecessor_sha256=PHASE4C_HTTP_IMPLEMENTATION_REPORT_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight hardening WORM successor" \
    '93d2c3779f6f0b11035d8fc46b6ed3070efd85977e43caa7ddba39df133d4344' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight hardening build-context" \
    'a23335b57752d5d8378694d3d98c84a2940c31fc547207804c29a00eb142dc17' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight hardening Dockerfile" \
    'dockerfile_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_DOCKERFILE_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight hardening predecessor" \
    'predecessor_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_REPORT_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core WORM successor" \
    'db1ffe2eaed03138fb75fd1007d032448960c502416ada92bec3d0846f4eaf0f' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core build-context" \
    '29372c7cb33edc16536d9fe10dacd1b7a5de669bcbcc8da21cc73496ce261ffc' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core Dockerfile" \
    'dockerfile_sha256=PHASE4C_TAG_OPERATOR_CORE_DOCKERFILE_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core predecessor" \
    'predecessor_sha256=PHASE4C_TAG_GLOBAL_PREFLIGHT_HARDENING_REPORT_SHA256' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C target-execution successor contract" \
    'load_http_target_execution_successor_contract(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C target-execution post-push successor module" \
    'tools.phase4c_http_target_execution_post_push_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C target-execution post-push successor contract" \
    'load_http_target_execution_post_push_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C target-execution post-push anchor successor module" \
    'tools.phase4c_http_target_execution_post_push_anchor_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C target-execution post-push anchor successor contract" \
    'load_http_target_execution_post_push_anchor_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP typed-normalization successor module" \
    'tools.phase4c_http_typed_normalization_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP typed-normalization successor contract" \
    'load_http_typed_normalization_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP typed-normalization anchor successor module" \
    'tools.phase4c_http_typed_normalization_anchor_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C HTTP typed-normalization anchor successor contract" \
    'load_http_typed_normalization_anchor_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight successor module" \
    'tools.phase4c_tag_migration_global_preflight_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag global-preflight successor contract" \
    'load_tag_global_preflight_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core successor module" \
    'tools.phase4c_tag_migration_operator_core_successor_acceptance' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"
assert_file_contains "Fixed Phase 4C tag operator-core successor contract" \
    'load_tag_operator_core_successor(ti_java_root)' \
    "$WORMHOLE_SUCCESSOR_VALIDATOR"

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
python3 "$WORMHOLE_SUCCESSOR_VALIDATOR" \
    --ti-java-root "$TI_JAVA_DIR" \
    --drift-manifest "$DRIFT_MANIFEST" \
    --dockerfile-sha256 "$current_dockerfile_sha" \
    --build-context-sha256 "$current_build_context_sha"

if grep -R --line-number --extended-regexp \
    'disabledWithoutDocker|withReuse|testcontainers\.reuse\.enable' \
    "$TI_JAVA_DIR/server/src/test"
then
    echo "Forbidden Testcontainers skip/reuse setting detected" >&2
    exit 1
fi

echo "Phase 2 static infrastructure checks passed"
