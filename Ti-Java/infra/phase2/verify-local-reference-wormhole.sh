#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
TI_JAVA_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/../.." && pwd -P)
DRIFT_MANIFEST="$SCRIPT_DIR/reference-drift-manifest.json"

POSTGRES_IMAGE='postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15'
REDIS_IMAGE='redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf'
EXPECTED_TABLES=70
EXPECTED_COLUMNS=617
EXPECTED_TARGET_VERSION='18.4'
EXPECTED_TARGET_VERSION_NUM='180004'

source_container=''
source_user=''
source_db=''
report_file="$SCRIPT_DIR/local-reference-verification.json"

usage() {
    cat <<'EOF'
Usage:
  verify-local-reference-wormhole.sh \
    --source-container NAME \
    --source-user USER \
    --source-db DATABASE \
    [--report /path/inside/Ti-Java/report.json]

The source must be an explicitly approved, non-production local PostgreSQL
container. No source password is accepted: access uses the source container's
existing local-socket authentication. The schema dump is transient and deleted.
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --source-container)
            source_container=${2-}
            shift 2
            ;;
        --source-user)
            source_user=${2-}
            shift 2
            ;;
        --source-db)
            source_db=${2-}
            shift 2
            ;;
        --report)
            report_file=${2-}
            shift 2
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$source_container" ] || [ -z "$source_user" ] || [ -z "$source_db" ]; then
    usage >&2
    exit 2
fi

case "$report_file" in
    /*) ;;
    *) report_file="$TI_JAVA_DIR/$report_file" ;;
esac
report_dir_input=$(dirname -- "$report_file")
report_name=$(basename -- "$report_file")
if [ ! -d "$report_dir_input" ]; then
    echo "Report parent directory must already exist: $report_dir_input" >&2
    exit 2
fi
report_dir=$(CDPATH= cd -- "$report_dir_input" && pwd -P) || {
    echo "Cannot resolve report parent directory: $report_dir_input" >&2
    exit 2
}
case "$report_dir" in
    "$TI_JAVA_DIR"|"$TI_JAVA_DIR"/*) ;;
    *)
        echo "Report path must physically stay inside Ti-Java: $report_file" >&2
        exit 2
        ;;
esac
case "$report_name" in
    ''|.|..)
        echo "Report filename is invalid: $report_name" >&2
        exit 2
        ;;
esac
report_file="$report_dir/$report_name"
if [ -L "$report_file" ] || [ -d "$report_file" ]; then
    echo "Report target must be a regular file, not a symlink or directory: $report_file" >&2
    exit 2
fi

command -v docker >/dev/null 2>&1 || {
    echo "Docker CLI is required" >&2
    exit 1
}

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

artifacts_dir="$SCRIPT_DIR/artifacts"
if [ -L "$artifacts_dir" ]; then
    echo "Artifacts directory must not be a symlink: $artifacts_dir" >&2
    exit 2
fi
if [ ! -e "$artifacts_dir" ]; then
    mkdir "$artifacts_dir"
fi
if [ ! -d "$artifacts_dir" ]; then
    echo "Artifacts path is not a directory: $artifacts_dir" >&2
    exit 2
fi
artifacts_dir=$(CDPATH= cd -- "$artifacts_dir" && pwd -P)
case "$artifacts_dir" in
    "$SCRIPT_DIR"/*) ;;
    *)
        echo "Artifacts directory escaped Phase 2 infrastructure: $artifacts_dir" >&2
        exit 2
        ;;
esac

run_id="$$"
work_dir="$artifacts_dir/wormhole-$run_id"
network="ti-phase2-wormhole-$run_id"
volume="ti-phase2-wormhole-pg-$run_id"
target_container="ti-phase2-wormhole-postgres-$run_id"
redis_container="ti-phase2-wormhole-redis-$run_id"
java_container="ti-phase2-wormhole-java-$run_id"
java_image="ti-java-server:phase2-wormhole-$run_id"
report_tmp=''
work_dir_created=false
network_id=''
volume_created=false
target_container_id=''
redis_container_id=''
java_container_id=''
java_image_created=false

source_container_id=$(docker container inspect --format '{{.Id}}' \
    "$source_container" 2>/dev/null || true)
source_container_name=$(docker container inspect --format '{{.Name}}' \
    "$source_container" 2>/dev/null | sed 's#^/##' || true)
source_container_state=$(docker container inspect --format '{{.State.Status}}' \
    "$source_container" 2>/dev/null || true)
if [ -z "$source_container_id" ] || [ "$source_container_state" != 'running' ]; then
    echo "Approved local source container is not running: $source_container" >&2
    exit 1
fi
case "$source_container_name" in
    "$target_container"|"$redis_container"|"$java_container")
        echo "Source container name collides with an isolated resource: $source_container_name" >&2
        exit 1
        ;;
esac
for planned_container in "$target_container" "$redis_container" "$java_container"; do
    if docker container inspect "$planned_container" >/dev/null 2>&1; then
        echo "Planned isolated container name already exists: $planned_container" >&2
        exit 1
    fi
done
if docker network inspect "$network" >/dev/null 2>&1; then
    echo "Planned isolated network already exists: $network" >&2
    exit 1
fi
if docker volume inspect "$volume" >/dev/null 2>&1; then
    echo "Planned isolated volume already exists: $volume" >&2
    exit 1
fi
if docker image inspect "$java_image" >/dev/null 2>&1; then
    echo "Planned transient Java image tag already exists: $java_image" >&2
    exit 1
fi
if [ -e "$work_dir" ]; then
    echo "Planned transient work directory already exists: $work_dir" >&2
    exit 1
fi

cleanup() {
    status=$?
    trap - 0
    set +e
    if [ -n "$java_container_id" ] && [ "$java_container_id" != "$source_container_id" ]; then
        docker rm --force --volumes "$java_container_id" >/dev/null 2>&1
    fi
    if [ -n "$redis_container_id" ] && [ "$redis_container_id" != "$source_container_id" ]; then
        docker rm --force --volumes "$redis_container_id" >/dev/null 2>&1
    fi
    if [ -n "$target_container_id" ] && [ "$target_container_id" != "$source_container_id" ]; then
        docker rm --force --volumes "$target_container_id" >/dev/null 2>&1
    fi
    if [ "$volume_created" = true ]; then
        docker volume rm "$volume" >/dev/null 2>&1
    fi
    if [ -n "$network_id" ]; then
        docker network rm "$network_id" >/dev/null 2>&1
    fi
    if [ "$java_image_created" = true ]; then
        docker image rm "$java_image" >/dev/null 2>&1
    fi
    if [ "$work_dir_created" = true ]; then
        rm -rf "$work_dir"
    fi
    if [ -n "$report_tmp" ]; then
        rm -f "$report_tmp"
    fi
    exit "$status"
}
trap cleanup 0
trap 'exit 130' 2
trap 'exit 143' 15

umask 077
mkdir "$work_dir"
work_dir_created=true
report_tmp=$(mktemp "$report_dir/.local-reference-verification.XXXXXX")

raw_dump="$work_dir/reference-schema.raw.sql"
schema_dump="$work_dir/reference-schema.sql"
owner_password_file="$work_dir/postgres.owner.password"
read_password_file="$work_dir/ti.db.password"
redis_password_file="$work_dir/ti.redis.password"
login_rate_limit_key_secret_file="$work_dir/ti.login-rate-limit.key-secret"
redis_config_file="$work_dir/redis.conf"
sql_error_file="$work_dir/read-role-error.log"

owner_password="phase2-$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
read_password="phase2-$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
redis_password="phase2-$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
login_rate_limit_key_secret="phase2-$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
printf '%s\n' "$owner_password" > "$owner_password_file"
printf '%s\n' "$read_password" > "$read_password_file"
printf '%s\n' "$redis_password" > "$redis_password_file"
printf '%s\n' "$login_rate_limit_key_secret" > "$login_rate_limit_key_secret_file"
printf 'bind 0.0.0.0\nprotected-mode no\nrequirepass %s\nappendonly no\nsave ""\n' \
    "$redis_password" > "$redis_config_file"
chmod 0444 "$owner_password_file" "$read_password_file" \
    "$redis_password_file" "$login_rate_limit_key_secret_file" \
    "$redis_config_file"

expected_legacy_commit=$(sed -n 's/.*"legacySourceCommit": "\([^"]*\)".*/\1/p' \
    "$DRIFT_MANIFEST" | head -n 1)
expected_alembic_head=$(sed -n 's/.*"alembicHead": "\([^"]*\)".*/\1/p' \
    "$DRIFT_MANIFEST" | head -n 1)
if [ -z "$expected_legacy_commit" ] || [ -z "$expected_alembic_head" ]; then
    echo "Reference drift manifest is missing legacy commit or Alembic head" >&2
    exit 1
fi

source_version=$(docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" psql --no-psqlrc --tuples-only --no-align \
    --username "$source_user" --dbname "$source_db" --command "SHOW server_version")
source_version_num=$(docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" psql --no-psqlrc --tuples-only --no-align \
    --username "$source_user" --dbname "$source_db" --command "SHOW server_version_num")
source_tables=$(docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" psql --no-psqlrc --tuples-only --no-align \
    --username "$source_user" --dbname "$source_db" --command \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
source_columns=$(docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" psql --no-psqlrc --tuples-only --no-align \
    --username "$source_user" --dbname "$source_db" --command \
    "SELECT count(*) FROM information_schema.columns WHERE table_schema='public'")
source_alembic_head=$(docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" psql --no-psqlrc --tuples-only --no-align \
    --username "$source_user" --dbname "$source_db" --command \
    "SELECT version_num FROM public.alembic_version")

if [ "$source_tables" != "$EXPECTED_TABLES" ] || [ "$source_columns" != "$EXPECTED_COLUMNS" ]; then
    echo "Approved local source shape drifted: expected 70/617, got $source_tables/$source_columns" >&2
    exit 1
fi
if [ "$source_alembic_head" != "$expected_alembic_head" ]; then
    echo "Approved local source Alembic head drifted: expected $expected_alembic_head, got $source_alembic_head" >&2
    exit 1
fi

docker exec --env 'PGOPTIONS=-c default_transaction_read_only=on' \
    "$source_container" pg_dump \
    --schema-only \
    --no-owner \
    --no-privileges \
    --username "$source_user" \
    --dbname "$source_db" > "$raw_dump"

# PostgreSQL 18 emits a random psql \restrict token. It is a client-side safety
# guard, not schema; remove it so the schema-only evidence has a stable hash.
grep --extended-regexp --invert-match '^\\(un)?restrict ' "$raw_dump" > "$schema_dump"
schema_sha256=$(sha256_file "$schema_dump")

network_id=$(docker network create --internal "$network")
docker volume create "$volume" >/dev/null
volume_created=true
target_container_id=$(docker run --detach \
    --name "$target_container" \
    --network "$network" \
    --network-alias postgres \
    --security-opt no-new-privileges:true \
    --mount "type=volume,source=$volume,target=/var/lib/postgresql" \
    --mount "type=bind,source=$owner_password_file,target=/run/secrets/postgres.owner.password,readonly" \
    --env POSTGRES_DB=ti_phase2_wormhole \
    --env POSTGRES_USER=phase2_owner \
    --env POSTGRES_PASSWORD_FILE=/run/secrets/postgres.owner.password \
    "$POSTGRES_IMAGE")
if [ "$target_container_id" = "$source_container_id" ]; then
    echo "Isolated PostgreSQL unexpectedly resolved to the source container" >&2
    exit 1
fi

ready=false
attempt=0
while [ "$attempt" -lt 60 ]; do
    ready_events=$(docker logs "$target_container" 2>&1 \
        | grep --count 'database system is ready to accept connections' || true)
    if [ "$ready_events" -ge 2 ] \
        && docker exec "$target_container" pg_isready --quiet \
            --username phase2_owner --dbname ti_phase2_wormhole; then
        ready=true
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done
if [ "$ready" != true ]; then
    docker logs "$target_container" >&2
    echo "Isolated PostgreSQL 18.4 restore target did not become ready" >&2
    exit 1
fi

docker exec --interactive "$target_container" psql \
    --no-psqlrc --set=ON_ERROR_STOP=1 \
    --username phase2_owner --dbname ti_phase2_wormhole < "$raw_dump" >/dev/null

target_version=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username phase2_owner --dbname ti_phase2_wormhole --command "SHOW server_version")
target_version_num=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username phase2_owner --dbname ti_phase2_wormhole --command "SHOW server_version_num")
target_tables=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username phase2_owner --dbname ti_phase2_wormhole --command \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")
target_columns=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username phase2_owner --dbname ti_phase2_wormhole --command \
    "SELECT count(*) FROM information_schema.columns WHERE table_schema='public'")

if [ "$target_version" != "$EXPECTED_TARGET_VERSION" ] \
    || [ "$target_version_num" != "$EXPECTED_TARGET_VERSION_NUM" ]; then
    echo "Restore target version drifted: $target_version / $target_version_num" >&2
    exit 1
fi
if [ "$target_tables" != "$EXPECTED_TABLES" ] || [ "$target_columns" != "$EXPECTED_COLUMNS" ]; then
    echo "Restored schema shape mismatch: expected 70/617, got $target_tables/$target_columns" >&2
    exit 1
fi

{
    printf '%s\n' '\set ON_ERROR_STOP on'
    printf "CREATE ROLE ti_phase2_read LOGIN PASSWORD '%s' NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION;\n" \
        "$read_password"
    printf '%s\n' \
        'ALTER ROLE ti_phase2_read SET default_transaction_read_only = on;' \
        'GRANT CONNECT ON DATABASE ti_phase2_wormhole TO ti_phase2_read;' \
        'REVOKE TEMPORARY ON DATABASE ti_phase2_wormhole FROM PUBLIC;' \
        'REVOKE TEMPORARY ON DATABASE ti_phase2_wormhole FROM ti_phase2_read;' \
        'GRANT USAGE ON SCHEMA public TO ti_phase2_read;' \
        'REVOKE CREATE ON SCHEMA public FROM PUBLIC;' \
        'REVOKE ALL PRIVILEGES ON ALL TABLES IN SCHEMA public FROM ti_phase2_read;' \
        'REVOKE ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public FROM ti_phase2_read;' \
        'GRANT SELECT ON ALL TABLES IN SCHEMA public TO ti_phase2_read;'
} | docker exec --interactive "$target_container" psql --no-psqlrc \
    --username phase2_owner --dbname ti_phase2_wormhole >/dev/null

readonly_default=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username ti_phase2_read --dbname ti_phase2_wormhole --command \
    "SHOW default_transaction_read_only")
readonly_temp=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username ti_phase2_read --dbname ti_phase2_wormhole --command \
    "SELECT has_database_privilege(current_user, current_database(), 'TEMPORARY')")
readonly_select=$(docker exec "$target_container" psql --no-psqlrc --tuples-only --no-align \
    --username ti_phase2_read --dbname ti_phase2_wormhole --command \
    "SELECT count(*) FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE'")

if [ "$readonly_default" != 'on' ] || [ "$readonly_temp" != 'f' ] \
    || [ "$readonly_select" != "$EXPECTED_TABLES" ]; then
    echo "Read role default, TEMP ACL, or SELECT capability is incorrect" >&2
    exit 1
fi

assert_acl_rejected() {
    label=$1
    sql=$2
    if docker exec --env 'PGOPTIONS=-c default_transaction_read_only=off' \
        "$target_container" psql --no-psqlrc --set=ON_ERROR_STOP=1 \
        --set=VERBOSITY=verbose --username ti_phase2_read \
        --dbname ti_phase2_wormhole --command "$sql" \
        > /dev/null 2> "$sql_error_file"; then
        echo "Read role unexpectedly passed $label with its read-only default disabled" >&2
        exit 1
    fi
    if ! grep --extended-regexp --quiet 'ERROR: *42501:' "$sql_error_file"; then
        echo "Read role $label failed for an unexpected reason" >&2
        sed -n '1,5p' "$sql_error_file" >&2
        exit 1
    fi
}

assert_acl_rejected INSERT "INSERT INTO subjects (name) VALUES ('forbidden')"
assert_acl_rejected UPDATE "UPDATE subjects SET description='forbidden' WHERE false"
assert_acl_rejected DELETE "DELETE FROM subjects WHERE false"
assert_acl_rejected DDL "CREATE TABLE forbidden_phase2_ddl (id integer)"
assert_acl_rejected TEMP_DDL "CREATE TEMPORARY TABLE forbidden_phase2_temp_ddl (id integer)"

redis_container_id=$(docker run --detach \
    --name "$redis_container" \
    --network "$network" \
    --network-alias redis \
    --read-only \
    --user 999:1000 \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --tmpfs /data:rw,noexec,nosuid,size=32m,uid=999,gid=1000,mode=0770 \
    --tmpfs /tmp:rw,noexec,nosuid,size=16m,uid=999,gid=1000,mode=1770 \
    --mount "type=bind,source=$redis_config_file,target=/run/secrets/redis.conf,readonly" \
    --entrypoint redis-server \
    "$REDIS_IMAGE" /run/secrets/redis.conf)

redis_ready=false
attempt=0
while [ "$attempt" -lt 30 ]; do
    if docker exec "$redis_container" sh -ec \
        'password=$(sed -n "s/^requirepass //p" /run/secrets/redis.conf); REDISCLI_AUTH=$password redis-cli --no-auth-warning ping' \
        2>/dev/null | grep --quiet '^PONG$'; then
        redis_ready=true
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done
if [ "$redis_ready" != true ]; then
    docker logs "$redis_container" >&2
    echo "Isolated Redis did not become ready" >&2
    exit 1
fi

BUILDKIT_PROGRESS=plain docker build --quiet \
    --file "$TI_JAVA_DIR/server/Dockerfile" \
    --tag "$java_image" \
    "$TI_JAVA_DIR/server" >/dev/null
java_image_created=true

java_container_id=$(docker run --detach \
    --name "$java_container" \
    --network "$network" \
    --network-alias api \
    --read-only \
    --cap-drop ALL \
    --security-opt no-new-privileges:true \
    --tmpfs /tmp:rw,noexec,nosuid,size=128m,uid=10001,gid=10001,mode=1770 \
    --mount "type=bind,source=$read_password_file,target=/run/secrets/ti.db.password,readonly" \
    --mount "type=bind,source=$redis_password_file,target=/run/secrets/ti.redis.password,readonly" \
    --mount "type=bind,source=$login_rate_limit_key_secret_file,target=/run/secrets/ti.login-rate-limit.key-secret,readonly" \
    --env SPRING_PROFILES_ACTIVE=prod \
    --env TI_DB_URL=jdbc:postgresql://postgres:5432/ti_phase2_wormhole \
    --env TI_DB_USERNAME=ti_phase2_read \
    --env TI_DB_POOL_MAX=2 \
    --env TI_DB_POOL_MIN=1 \
    --env TI_REDIS_HOST=redis \
    --env TI_REDIS_PORT=6379 \
    "$java_image")

java_started=false
attempt=0
while [ "$attempt" -lt 90 ]; do
    if [ "$(docker inspect --format '{{.State.Running}}' "$java_container" 2>/dev/null || true)" != 'true' ]; then
        docker logs "$java_container" >&2
        echo "Java image exited before Hibernate schema validation completed" >&2
        exit 1
    fi
    if docker logs "$java_container" 2>&1 | grep --quiet 'Started TiApplication'; then
        java_started=true
        break
    fi
    attempt=$((attempt + 1))
    sleep 1
done
if [ "$java_started" != true ]; then
    docker logs "$java_container" >&2
    echo "Java image did not start against the restored 70-table schema" >&2
    exit 1
fi

if ! docker exec "$java_container" bash -ec \
    'exec 3<>/dev/tcp/127.0.0.1/8080; printf "GET /readyz HTTP/1.0\r\nHost: localhost\r\n\r\n" >&3; response=$(cat <&3); printf "%s" "$response" | grep -q "\"status\":\"UP\""'; then
    docker logs "$java_container" >&2
    echo "Java readiness did not become UP after Hibernate validate" >&2
    exit 1
fi

captured_at=$(LC_ALL=C date -u '+%Y-%m-%dT%H:%M:%SZ')
dockerfile_sha256=$(sha256_file "$TI_JAVA_DIR/server/Dockerfile")
java_build_context_sha256=$("$SCRIPT_DIR/hash-java-build-context.sh")

cat > "$report_tmp" <<EOF
{
  "schemaVersion": 1,
  "capturedAt": "$captured_at",
  "source": {
    "classification": "explicitly-approved-local-development-reference",
    "legacySourceCommit": "$expected_legacy_commit",
    "alembicHead": "$source_alembic_head",
    "serverVersion": "$source_version",
    "serverVersionNum": "$source_version_num",
    "publicBaseTables": $source_tables,
    "publicColumns": $source_columns
  },
  "restore": {
    "image": "$POSTGRES_IMAGE",
    "serverVersion": "$target_version",
    "serverVersionNum": "$target_version_num",
    "publicBaseTables": $target_tables,
    "publicColumns": $target_columns,
    "canonicalSchemaDumpSha256": "$schema_sha256",
    "schemaDumpPersisted": false
  },
  "readRole": {
    "selectPassed": true,
    "defaultTransactionReadOnly": true,
    "temporaryPrivilege": false,
    "aclVerifiedWithReadOnlyDefaultDisabled": true,
    "insertRejected": true,
    "updateRejected": true,
    "deleteRejected": true,
    "ddlRejected": true,
    "temporaryDdlRejected": true
  },
  "java": {
    "dockerfileSha256": "$dockerfile_sha256",
    "buildContextSha256": "$java_build_context_sha256",
    "hibernateDdlAuto": "validate",
    "startupPassed": true,
    "readinessPassed": true
  },
  "productionDatabaseVersion": "unknown",
  "flywayBaselineCreated": false
}
EOF

chmod 0644 "$report_tmp"
mv "$report_tmp" "$report_file"

echo "Phase 2 local-reference wormhole passed"
echo "Evidence report: $report_file"
