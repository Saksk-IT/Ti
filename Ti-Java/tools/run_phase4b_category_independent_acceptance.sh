#!/usr/bin/env bash
set -euo pipefail

umask 077

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
SOURCE="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
REPO="$(CDPATH= cd -- "$SOURCE/.." && pwd -P)"
SOURCE_PYTHON_EXPLICIT=false
if [ "${SOURCE_PYTHON+x}" = x ]; then
    SOURCE_PYTHON_EXPLICIT=true
fi
EXPECTED_SOURCE_PYTHON="$REPO/.venv/bin/python"
SOURCE_PYTHON="${SOURCE_PYTHON:-$EXPECTED_SOURCE_PYTHON}"
ORIGINAL_DOCKER_CONFIG="${DOCKER_CONFIG:-${HOME:?HOME is required to locate Docker CLI plugins}/.docker}"
KEEP_WORKDIR=false
REPORT=""

usage() {
    printf '%s\n' \
        "Usage: $0 [--report TARGET_PATH] [--keep-workdir]" \
        "" \
        "TARGET_PATH must remain below server/target and must not already exist." \
        "SOURCE_PYTHON may name the repository .venv interpreter used for the" \
        "canonical frozen-source tests. The independent copy never uses it."
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --report)
            [ "$#" -ge 2 ] || { usage >&2; exit 2; }
            REPORT="$2"
            shift 2
            ;;
        --keep-workdir)
            KEEP_WORKDIR=true
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        *)
            usage >&2
            exit 2
            ;;
    esac
done

for command_name in docker git rsync python3 node curl jq; do
    command -v "$command_name" >/dev/null 2>&1 || {
        printf 'Required command is unavailable: %s\n' "$command_name" >&2
        exit 1
    }
done
ORIGINAL_DOCKER_CONFIG="$(python3 - "$ORIGINAL_DOCKER_CONFIG" <<'PY'
import pathlib
import sys

print(pathlib.Path(sys.argv[1]).expanduser().resolve())
PY
)"
command -v "$SOURCE_PYTHON" >/dev/null 2>&1 || {
    printf 'SOURCE_PYTHON is unavailable: %s\n' "$SOURCE_PYTHON" >&2
    exit 1
}
source_python_path="$(
    source_python_command="$(command -v "$SOURCE_PYTHON")"
    CDPATH= cd -- "$(dirname -- "$source_python_command")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename -- "$source_python_command")"
)"
expected_source_python_path="$(
    CDPATH= cd -- "$(dirname -- "$EXPECTED_SOURCE_PYTHON")"
    printf '%s/%s\n' "$(pwd -P)" "$(basename -- "$EXPECTED_SOURCE_PYTHON")"
)"
[ "$source_python_path" = "$expected_source_python_path" ] || {
    printf 'SOURCE_PYTHON must be the repository legacy venv: %s\n' \
        "$EXPECTED_SOURCE_PYTHON" >&2
    exit 1
}
"$SOURCE_PYTHON" -c 'import flask, sqlalchemy' || {
    printf '%s\n' 'SOURCE_PYTHON lacks the frozen legacy dependencies' >&2
    exit 1
}
[ "${DOCKER_HOST+x}" != x ] \
    && [ "${DOCKER_CONTEXT+x}" != x ] \
    && [ "${DOCKER_TLS+x}" != x ] \
    && [ "${DOCKER_TLS_VERIFY+x}" != x ] \
    && [ "${DOCKER_CERT_PATH+x}" != x ] || {
    printf '%s\n' \
        'Docker endpoint and TLS environment overrides must be unset for local acceptance' >&2
    exit 1
}
SOURCE_DOCKER_CONTEXT="$(docker context show)"
DOCKER_ENDPOINT="$(
    docker context inspect "$SOURCE_DOCKER_CONTEXT" \
        --format '{{(index .Endpoints "docker").Host}}'
)"
[ -n "$DOCKER_ENDPOINT" ] || {
    printf '%s\n' 'Current Docker context has no daemon endpoint' >&2
    exit 1
}
case "$DOCKER_ENDPOINT" in
    unix:///*) ;;
    *)
        printf '%s\n' 'Current Docker context must use a local Unix socket' >&2
        exit 1
        ;;
esac
LOCAL_DOCKER_SOCKET="${DOCKER_ENDPOINT#unix://}"
[ -S "$LOCAL_DOCKER_SOCKET" ] || {
    printf '%s\n' 'Current Docker context Unix socket is unavailable' >&2
    exit 1
}
STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM}"
LOWER_STAMP="$(printf '%s' "$STAMP" | tr '[:upper:]' '[:lower:]')"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ti-phase4b-category-independent.XXXXXX")"
DOCKER_CONFIG="$WORK/docker-config"
EXPECTED_DOCKER_CONFIG="$WORK/docker-config.expected.json"
BUILDX_CONFIG="$WORK/buildx-config"
DOCKER_HOST="$DOCKER_ENDPOINT"
export DOCKER_CONFIG BUILDX_CONFIG DOCKER_HOST
unset DOCKER_CONTEXT DOCKER_AUTH_CONFIG BUILDKIT_HOST BUILDX_BUILDER
unset DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH
readonly SOURCE_DOCKER_CONTEXT DOCKER_ENDPOINT LOCAL_DOCKER_SOCKET DOCKER_HOST
readonly DOCKER_CONFIG BUILDX_CONFIG
STAGE="$WORK/stage"
COPY="$STAGE/Ti-Java"
LIST0="$WORK/controlled-files.nul"
PROJECT="ti-p4b-category-$LOWER_STAMP"
IMAGE="ti-java-phase4b-category:$LOWER_STAMP"
MAVEN_CACHE="ti-java-phase4b-category-m2-$LOWER_STAMP"
OVERRIDE="$WORK/compose.acceptance.yml"
SOURCE_MANIFEST="$WORK/source-manifest.json"
COPY_MANIFEST="$WORK/copy-manifest.json"
SOURCE_NONRECURSIVE_MANIFEST="$WORK/source-manifest-nonrecursive.json"
COPY_NONRECURSIVE_MANIFEST="$WORK/copy-manifest-nonrecursive.json"
ACCEPTANCE_CONTROLLED_PATH="Ti-Java/docs/refactor/phase4b/personal-bank-category-acceptance.json"
SOURCE_TOOLS_LOG="$WORK/source-tools.log"
NODE_LOG="$WORK/miniprogram-node.log"
MAVEN_LOG="$WORK/maven.log"
DATA_PLANE_LOG="$WORK/data-plane.log"
BASELINE_CONTAINERS="$WORK/baseline-containers.txt"
BASELINE_NETWORKS="$WORK/baseline-networks.txt"
BASELINE_VOLUMES="$WORK/baseline-volumes.txt"
REPORT_TEMP=""
REPORT_PUBLISHED=false
CLEANED=false
WORK_CLEANED=false
API_PORT=""
POSTGRES_PORT=""
REPORT_ROOT="$SOURCE/server/target"
LOCK_DIR="$REPORT_ROOT/phase4b-category-independent-acceptance.lock"
LOCK_OWNER="$LOCK_DIR/owner-token"
LOCK_HELD=false
LOCK_TOKEN=""

compose() {
    docker compose \
        --project-name "$PROJECT" \
        --env-file "$COPY/.env.example" \
        --file "$COPY/compose.dev.yml" \
        --file "$OVERRIDE" \
        "$@"
}

cleanup_owned_resources() {
    set +e
    if [ -f "$OVERRIDE" ] && [ -d "$COPY" ]; then
        compose down --volumes --remove-orphans --timeout 20 >/dev/null 2>&1
    fi
    owned_containers="$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" 2>/dev/null)"
    if [ -n "$owned_containers" ]; then
        for owned_container in $owned_containers; do
            docker rm --force "$owned_container" >/dev/null 2>&1
        done
    fi
    docker network rm "$PROJECT-backend" "$PROJECT-host-access" >/dev/null 2>&1
    docker volume rm \
        "$PROJECT-postgres-data" \
        "$PROJECT-redis-data" \
        "$MAVEN_CACHE" >/dev/null 2>&1
    docker image rm "$IMAGE" >/dev/null 2>&1
    CLEANED=true
    set -e
}

verify_acceptance_lock_ownership() {
    [ "$LOCK_HELD" = true ]
    [ -n "$LOCK_TOKEN" ]
    [ -d "$LOCK_DIR" ] && [ ! -L "$LOCK_DIR" ]
    [ -f "$LOCK_OWNER" ] && [ ! -L "$LOCK_OWNER" ]
    [ "$(cat "$LOCK_OWNER")" = "$LOCK_TOKEN" ]
}

release_acceptance_lock() {
    verify_acceptance_lock_ownership || return 1
    rm -f -- "$LOCK_OWNER" || return 1
    rmdir -- "$LOCK_DIR" || return 1
    LOCK_HELD=false
}

on_exit() {
    exit_code=$?
    trap - EXIT HUP INT TERM
    set +e
    if [ "$CLEANED" != true ]; then
        cleanup_owned_resources
        set +e
    fi
    if [ -n "$REPORT_TEMP" ]; then
        rm -f -- "$REPORT_TEMP"
    fi
    if [ "$KEEP_WORKDIR" = true ]; then
        printf 'Diagnostic work directory retained: %s\n' "$WORK" >&2
    elif [ "$WORK_CLEANED" != true ]; then
        if ! rm -rf -- "$WORK"; then
            printf 'Failed to remove diagnostic work directory: %s\n' "$WORK" >&2
            if [ "$exit_code" -eq 0 ]; then
                exit_code=1
            fi
        else
            WORK_CLEANED=true
        fi
    fi
    if [ "$LOCK_HELD" = true ]; then
        if ! release_acceptance_lock; then
            printf 'Failed to release acceptance lock: %s\n' "$LOCK_DIR" >&2
            if [ "$exit_code" -eq 0 ]; then
                exit_code=1
            fi
        fi
        LOCK_HELD=false
    fi
    if [ "$exit_code" -ne 0 ] && [ "$REPORT_PUBLISHED" = true ]; then
        if ! rm -f -- "$REPORT"; then
            printf 'Failed to remove invalid acceptance report: %s\n' "$REPORT" >&2
        fi
        REPORT_PUBLISHED=false
    fi
    exit "$exit_code"
}
trap on_exit EXIT
trap 'exit 130' HUP INT TERM

[ ! -L "$REPORT_ROOT" ] || {
    printf '%s\n' 'server/target must not be a symlink' >&2
    exit 1
}
mkdir -p "$REPORT_ROOT"
[ -d "$REPORT_ROOT" ] && [ ! -L "$REPORT_ROOT" ]
if ! mkdir -- "$LOCK_DIR"; then
    printf '%s\n' 'Another Phase 4B category independent acceptance run holds the lock' >&2
    exit 1
fi
LOCK_HELD=true
LOCK_TOKEN="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
printf '%s\n' "$LOCK_TOKEN" > "$LOCK_OWNER"
verify_acceptance_lock_ownership

mkdir -p "$DOCKER_CONFIG" "$BUILDX_CONFIG"
python3 - "$DOCKER_CONFIG/config.json" "$EXPECTED_DOCKER_CONFIG" <<'PY'
import json
import pathlib
import sys

content = json.dumps(
    {"auths": {}},
    sort_keys=True,
) + "\n"
for raw_path in sys.argv[1:]:
    pathlib.Path(raw_path).write_text(content, encoding="utf-8")
PY
if [ -d "$ORIGINAL_DOCKER_CONFIG/cli-plugins" ]; then
    ln -s "$ORIGINAL_DOCKER_CONFIG/cli-plugins" "$DOCKER_CONFIG/cli-plugins"
fi

verify_docker_client_isolation() {
    [ "$DOCKER_CONFIG" = "$WORK/docker-config" ]
    [ "$DOCKER_HOST" = "$DOCKER_ENDPOINT" ]
    [ "$BUILDX_CONFIG" = "$WORK/buildx-config" ]
    [ -d "$DOCKER_CONFIG" ] && [ ! -L "$DOCKER_CONFIG" ]
    [ -d "$BUILDX_CONFIG" ] && [ ! -L "$BUILDX_CONFIG" ]
    [ "${DOCKER_CONTEXT+x}" != x ]
    [ "${DOCKER_AUTH_CONFIG+x}" != x ]
    [ "${BUILDKIT_HOST+x}" != x ] && [ "${BUILDX_BUILDER+x}" != x ]
    [ "${DOCKER_TLS+x}" != x ]
    [ "${DOCKER_TLS_VERIFY+x}" != x ] && [ "${DOCKER_CERT_PATH+x}" != x ]
    [ -S "$LOCAL_DOCKER_SOCKET" ]
    [ -f "$DOCKER_CONFIG/config.json" ] && [ ! -L "$DOCKER_CONFIG/config.json" ]
    cmp "$EXPECTED_DOCKER_CONFIG" "$DOCKER_CONFIG/config.json"
    [ ! -e "$DOCKER_CONFIG/contexts" ] && [ ! -L "$DOCKER_CONFIG/contexts" ]
    for tls_file in ca.pem cert.pem key.pem; do
        [ ! -e "$DOCKER_CONFIG/$tls_file" ] && [ ! -L "$DOCKER_CONFIG/$tls_file" ]
    done
    if [ -d "$ORIGINAL_DOCKER_CONFIG/cli-plugins" ]; then
        [ -L "$DOCKER_CONFIG/cli-plugins" ]
        [ "$(readlink "$DOCKER_CONFIG/cli-plugins")" = "$ORIGINAL_DOCKER_CONFIG/cli-plugins" ]
    else
        [ ! -e "$DOCKER_CONFIG/cli-plugins" ] && [ ! -L "$DOCKER_CONFIG/cli-plugins" ]
    fi
}

verify_maven_container_socket_binding() {
    [ "$(grep -F -- '--volume /var/run/docker.sock:/var/run/docker.sock' \
        "$COPY/infra/phase2/verify-in-maven-container.sh" | wc -l | tr -d ' ')" -eq 2 ]
    python3 - "$LOCAL_DOCKER_SOCKET" /var/run/docker.sock <<'PY'
import os
import pathlib
import stat
import sys

pinned = pathlib.Path(sys.argv[1])
maven_mount_source = pathlib.Path(sys.argv[2])
for label, path in (("pinned", pinned), ("Maven mount source", maven_mount_source)):
    if not path.is_absolute():
        raise SystemExit(f"{label} Docker socket path is not absolute")
    try:
        mode = path.stat().st_mode
    except OSError as exc:
        raise SystemExit(f"{label} Docker socket is unavailable") from exc
    if not stat.S_ISSOCK(mode):
        raise SystemExit(f"{label} Docker endpoint is not a Unix socket")
if not os.path.samefile(pinned, maven_mount_source):
    raise SystemExit("Maven container Docker socket differs from the pinned socket")
PY
}

verify_docker_client_isolation
docker compose version >/dev/null
docker buildx version >/dev/null
docker info >/dev/null 2>&1 || {
    printf '%s\n' 'Docker daemon is unavailable' >&2
    exit 1
}
verify_docker_client_isolation
if [ -z "$REPORT" ]; then
    REPORT="$REPORT_ROOT/phase4b-category-independent-acceptance-$STAMP.json"
fi
REPORT="$(python3 - "$REPORT_ROOT" "$REPORT" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
candidate = pathlib.Path(sys.argv[2])
if not candidate.is_absolute():
    candidate = pathlib.Path.cwd() / candidate
parent = candidate.parent.resolve(strict=True)
if parent != root:
    raise SystemExit("acceptance report must be a direct child of server/target")
candidate = parent / candidate.name
if candidate.exists() or candidate.is_symlink() or not candidate.name:
    raise SystemExit("acceptance report already exists")
print(candidate)
PY
)"

docker ps -aq | LC_ALL=C sort > "$BASELINE_CONTAINERS"
docker network ls -q | LC_ALL=C sort > "$BASELINE_NETWORKS"
docker volume ls -q | LC_ALL=C sort > "$BASELINE_VOLUMES"

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | awk '{print $1}'
    else
        shasum -a 256 "$1" | awk '{print $1}'
    fi
}

pick_port() {
    python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

make_manifest() {
    manifest_root="$1"
    manifest_output="$2"
    manifest_exclusion="${3:-}"
    python3 - "$manifest_root" "$LIST0" "$manifest_output" "$manifest_exclusion" <<'PY'
import hashlib
import json
import os
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
entries = pathlib.Path(sys.argv[2]).read_bytes().split(b"\0")
output = pathlib.Path(sys.argv[3])
exclusion = sys.argv[4]
records = []
excluded_count = 0
for raw in entries:
    if not raw:
        continue
    relative = os.fsdecode(raw)
    path = root / relative
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"invalid controlled path: {relative}")
    if exclusion and relative == exclusion:
        excluded_count += 1
        continue
    records.append({
        "path": relative.removeprefix("Ti-Java/"),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    })
payload = (json.dumps(
    records,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
) + "\n").encode()
output.write_bytes(payload)
if exclusion and excluded_count != 1:
    raise SystemExit("non-recursive manifest must exclude exactly one acceptance contract")
print(len(records))
PY
}

capture_controlled_list() {
    controlled_output="$1"
    python3 - "$REPO" "$controlled_output" <<'PY'
import os
import pathlib
import subprocess
import sys

root = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
raw = subprocess.check_output([
    "git", "-C", str(root), "ls-files",
    "-co", "--exclude-standard", "-z", "--", "Ti-Java",
])
paths = sorted({os.fsdecode(item) for item in raw.split(b"\0") if item})
for relative in paths:
    path = root / relative
    if path.is_symlink():
        raise SystemExit(f"controlled symlink is forbidden: {relative}")
    if not path.is_file():
        raise SystemExit(f"controlled path is not a regular file: {relative}")
output.write_bytes(b"\0".join(os.fsencode(item) for item in paths) + b"\0")
print(f"controlled_file_count={len(paths)}")
PY
}

assert_port_released() {
    python3 - "$1" <<'PY'
import socket
import sys
import time

port = int(sys.argv[1])
for _ in range(20):
    with socket.socket() as sock:
        sock.settimeout(0.25)
        if sock.connect_ex(("127.0.0.1", port)) != 0:
            raise SystemExit(0)
    time.sleep(0.25)
raise SystemExit(f"listener remains on 127.0.0.1:{port}")
PY
}

capture_controlled_list "$LIST0"
CONTROLLED_FILE_COUNT="$(make_manifest "$REPO" "$SOURCE_MANIFEST")"
MANIFEST_SHA256="$(hash_file "$SOURCE_MANIFEST")"
NONRECURSIVE_FILE_COUNT="$(
    make_manifest "$REPO" "$SOURCE_NONRECURSIVE_MANIFEST" "$ACCEPTANCE_CONTROLLED_PATH"
)"
[ "$NONRECURSIVE_FILE_COUNT" -eq $((CONTROLLED_FILE_COUNT - 1)) ]
NONRECURSIVE_MANIFEST_SHA256="$(hash_file "$SOURCE_NONRECURSIVE_MANIFEST")"

printf '%s\n' 'Running canonical frozen-source tests (explicitly outside the independent copy)'
(
    cd "$SOURCE"
    TI_PHASE4B_CATEGORY_PREFINAL_ACCEPTANCE=1 \
        TI_PHASE4B_CATEGORY_PREFINAL_LOCK_TOKEN="$LOCK_TOKEN" \
        PYTHONDONTWRITEBYTECODE=1 \
        "$SOURCE_PYTHON" -B \
        -m unittest discover -s tools -p 'test_*.py'
) 2>&1 | tee "$SOURCE_TOOLS_LOG"
python3 - "$SOURCE_TOOLS_LOG" <<'PY'
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
match = re.search(r"Ran (\d+) tests?", text)
if not match or int(match.group(1)) != 248 or not re.search(r"^OK$", text, re.MULTILINE):
    raise SystemExit("canonical frozen-source tests did not report 248/248")
PY

AFTER_TOOLS_LIST0="$WORK/controlled-files-after-tools.nul"
AFTER_TOOLS_MANIFEST="$WORK/source-manifest-after-tools.json"
capture_controlled_list "$AFTER_TOOLS_LIST0" >/dev/null
cmp "$LIST0" "$AFTER_TOOLS_LIST0"
[ "$(make_manifest "$REPO" "$AFTER_TOOLS_MANIFEST")" -eq "$CONTROLLED_FILE_COUNT" ]
cmp "$SOURCE_MANIFEST" "$AFTER_TOOLS_MANIFEST"

mkdir -p "$STAGE"
rsync -a --from0 --files-from="$LIST0" "$REPO/" "$STAGE/"
[ -d "$COPY" ]
[ ! -e "$COPY/server/target" ]
[ ! -e "$COPY/miniprogram/node_modules" ]
SYMLINK_COUNT="$(find "$COPY" -type l -print | wc -l | tr -d ' ')"
[ "$SYMLINK_COUNT" -eq 0 ]
FORBIDDEN_ARTIFACT_COUNT="$(
    find "$COPY" \
        \( -type d \( -name target -o -name node_modules -o -name .m2 \
            -o -name .venv -o -name __pycache__ -o -name .pytest_cache \) \
        -o -type f \( -name .env -o -name '*.pyc' -o -name '*.class' \) \) \
        -print | wc -l | tr -d ' '
)"
[ "$FORBIDDEN_ARTIFACT_COUNT" -eq 0 ]
FORBIDDEN_JAR_COUNT="$(
    find "$COPY" -type f -name '*.jar' \
        ! -path '*/.mvn/wrapper/maven-wrapper.jar' -print | wc -l | tr -d ' '
)"
[ "$FORBIDDEN_JAR_COUNT" -eq 0 ]

COPY_FILE_COUNT="$(make_manifest "$STAGE" "$COPY_MANIFEST")"
[ "$CONTROLLED_FILE_COUNT" -eq "$COPY_FILE_COUNT" ]
cmp "$SOURCE_MANIFEST" "$COPY_MANIFEST"
[ "$(
    make_manifest "$STAGE" "$COPY_NONRECURSIVE_MANIFEST" "$ACCEPTANCE_CONTROLLED_PATH"
)" -eq "$NONRECURSIVE_FILE_COUNT" ]
cmp "$SOURCE_NONRECURSIVE_MANIFEST" "$COPY_NONRECURSIVE_MANIFEST"
SOURCE_BUILD_SHA256="$("$SOURCE/infra/phase2/hash-java-build-context.sh")"
COPY_BUILD_SHA256="$("$COPY/infra/phase2/hash-java-build-context.sh")"
[ "$SOURCE_BUILD_SHA256" = "$COPY_BUILD_SHA256" ]

printf 'Independent copy contains %s controlled files; manifest=%s\n' \
    "$CONTROLLED_FILE_COUNT" "$MANIFEST_SHA256"

(
    cd "$COPY"
    python3 tools/validate_phase1.py
    ./infra/phase2/verify-static.sh
    ./infra/phase3/verify-static.sh
    ./infra/phase3/topology/verify-static.sh
)

(
    cd "$COPY"
    node --test miniprogram/tests/*.test.js
) 2>&1 | tee "$NODE_LOG"
python3 - "$NODE_LOG" <<'PY'
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
if not re.search(r"(?:^|\n)[^\n]*tests\s+36(?:\n|$)", text):
    raise SystemExit("independent miniprogram tests did not report 36 tests")
if not re.search(r"(?:^|\n)[^\n]*pass\s+36(?:\n|$)", text):
    raise SystemExit("independent miniprogram tests did not report 36 passes")
if not re.search(r"(?:^|\n)[^\n]*fail\s+0(?:\n|$)", text):
    raise SystemExit("independent miniprogram tests did not report zero failures")
PY

(
    cd "$COPY"
    verify_docker_client_isolation
    ./infra/phase3/topology/verify-data-plane.sh
    verify_docker_client_isolation
) 2>&1 | tee "$DATA_PLANE_LOG"

if docker volume inspect "$MAVEN_CACHE" >/dev/null 2>&1; then
    printf 'Dedicated Maven volume unexpectedly exists: %s\n' "$MAVEN_CACHE" >&2
    exit 1
fi
verify_maven_container_socket_binding
docker volume create "$MAVEN_CACHE" >/dev/null
MAVEN_IMAGE="maven:3.9.16-eclipse-temurin-25@sha256:7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c"
[ -z "$(docker run --rm --volume "$MAVEN_CACHE:/cache:ro" "$MAVEN_IMAGE" \
    sh -c 'find /cache -mindepth 1 -maxdepth 1 -print -quit')" ]

MAVEN_ATTEMPTS=0
MAVEN_MAX_ATTEMPTS=3
: > "$MAVEN_LOG"
while [ "$MAVEN_ATTEMPTS" -lt "$MAVEN_MAX_ATTEMPTS" ]; do
    MAVEN_ATTEMPTS=$((MAVEN_ATTEMPTS + 1))
    if (
        cd "$COPY"
        TI_JAVA_MAVEN_CACHE_VOLUME="$MAVEN_CACHE" \
            ./infra/phase2/verify-in-maven-container.sh clean verify
    ) 2>&1 | tee -a "$MAVEN_LOG"; then
        break
    fi
    if [ "$MAVEN_ATTEMPTS" -ge "$MAVEN_MAX_ATTEMPTS" ]; then
        printf 'Independent Maven verification failed after %s attempts\n' \
            "$MAVEN_ATTEMPTS" >&2
        exit 1
    fi
    printf 'Retrying independent Maven verification after transient transfer failure (%s/%s)\n' \
        "$MAVEN_ATTEMPTS" "$MAVEN_MAX_ATTEMPTS" >&2
done
verify_maven_container_socket_binding
verify_docker_client_isolation

python3 - "$COPY/server/target" "$WORK/maven-summary.json" <<'PY'
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

target = pathlib.Path(sys.argv[1])
output = pathlib.Path(sys.argv[2])
expected = {"surefire-reports": 424, "failsafe-reports": 60}
summary = {}
for folder, expected_tests in expected.items():
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    reports = sorted((target / folder).glob("TEST-*.xml"))
    if not reports:
        raise SystemExit(f"missing Maven XML reports: {folder}")
    for report in reports:
        root = ET.parse(report).getroot()
        for key in totals:
            totals[key] += int(float(root.attrib.get(key, "0")))
    required = {
        "tests": expected_tests,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
    }
    if totals != required:
        raise SystemExit(f"unexpected Maven totals for {folder}: {totals}")
    summary[folder] = totals
output.write_text(json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8")
PY

docker image inspect "$IMAGE" >/dev/null 2>&1 && {
    printf 'Unique image tag unexpectedly exists: %s\n' "$IMAGE" >&2
    exit 1
}
docker build --tag "$IMAGE" --file "$COPY/server/Dockerfile" "$COPY/server"

python3 - "$OVERRIDE" "$IMAGE" <<'PY'
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_text(
    "services:\n"
    "  api:\n"
    f"    image: {sys.argv[2]}\n"
    "    pull_policy: never\n",
    encoding="utf-8",
)
PY

API_PORT="$(pick_port)"
POSTGRES_PORT="$(pick_port)"
while [ "$POSTGRES_PORT" = "$API_PORT" ]; do
    POSTGRES_PORT="$(pick_port)"
done
export TI_JAVA_COMPOSE_PROJECT="$PROJECT"
export TI_JAVA_API_PORT="$API_PORT"
export TI_JAVA_POSTGRES_PORT="$POSTGRES_PORT"
export TI_SUBJECT_READ_RATE_LIMIT_NAMESPACE="$PROJECT:catalog:subject-read-rate"

compose config --quiet
compose up --detach --wait --wait-timeout 180 --no-build
for service in postgres redis api; do
    container_id="$(compose ps --quiet "$service")"
    [ -n "$container_id" ]
    [ "$(docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' "$container_id")" = 'running/healthy' ]
done
[ "$(compose ps --quiet | wc -l | tr -d ' ')" -eq 3 ]

PG_CID="$(compose ps --quiet postgres)"
REDIS_CID="$(compose ps --quiet redis)"
API_CID="$(compose ps --quiet api)"

[ "$(curl -sS -o "$WORK/livez.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/livez")" = 200 ]
[ "$(curl -sS -o "$WORK/readyz.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/readyz")" = 200 ]
[ "$(curl -sS -o "$WORK/unknown.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/__ti_java_unknown__")" = 401 ]
[ "$(curl -sS -o "$WORK/host-metrics.txt" -w '%{http_code}' "http://127.0.0.1:$API_PORT/actuator/prometheus")" = 404 ]
jq -e '.status == "UP"' "$WORK/livez.json" >/dev/null
jq -e '.status == "UP"' "$WORK/readyz.json" >/dev/null

docker exec "$API_CID" bash -ec '
exec 3<>/dev/tcp/127.0.0.1/9090
printf "GET /actuator/prometheus HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3
cat <&3
' > "$WORK/internal-metrics.http"
tr -d '\r' < "$WORK/internal-metrics.http" > "$WORK/internal-metrics.normalized"
grep -q '^HTTP/1.1 200' "$WORK/internal-metrics.normalized"
grep -q '^jvm_info' "$WORK/internal-metrics.normalized"

python3 - "$POSTGRES_PORT" <<'PY'
import socket
import sys
with socket.create_connection(("127.0.0.1", int(sys.argv[1])), timeout=5):
    pass
PY
docker exec "$PG_CID" pg_isready --quiet \
    --username ti_java_fixture_owner \
    --dbname ti_java_phase2

docker inspect "$PG_CID" "$REDIS_CID" "$API_CID" > "$WORK/runtime-inspect.json"
python3 - "$WORK/runtime-inspect.json" "$COPY" "$SOURCE" "$API_PORT" "$POSTGRES_PORT" "$IMAGE" "$PROJECT" <<'PY'
import json
import os
import pathlib
import sys

inspect_path, copy_raw, source_raw, api_port, pg_port, expected_image, expected_project = sys.argv[1:]
containers = json.loads(pathlib.Path(inspect_path).read_text(encoding="utf-8"))
copy_root = pathlib.Path(copy_raw).resolve()
source_root = pathlib.Path(source_raw).resolve()

def normalize(path):
    path = os.fspath(path)
    for prefix in ("/host_mnt", "/run/desktop/mnt/host"):
        if path == prefix or path.startswith(prefix + "/"):
            path = path[len(prefix):] or "/"
            break
    return pathlib.Path(os.path.realpath(path))

def inside(path, root):
    try:
        return os.path.commonpath((str(path), str(root))) == str(root)
    except ValueError:
        return False

by_service = {
    item["Config"]["Labels"]["com.docker.compose.service"]: item
    for item in containers
}
if set(by_service) != {"postgres", "redis", "api"}:
    raise SystemExit(f"unexpected compose services: {set(by_service)}")

def expected_source(relative_path):
    return str(normalize(copy_root / relative_path))

expected_policy = {
    "postgres": {
        "user": "70:70",
        "image": "postgres:18.4-alpine@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15",
        "memory": 768 * 1024 * 1024,
        "pids": 256,
        "tmpfs": {
            "/tmp": "rw,noexec,nosuid,size=64m,uid=70,gid=70,mode=1770",
            "/var/run/postgresql": "rw,noexec,nosuid,size=16m,uid=70,gid=70,mode=0770",
        },
        "port_bindings": {
            "5432/tcp": [{"HostIp": "127.0.0.1", "HostPort": pg_port}],
        },
        "binds": {
            "/docker-entrypoint-initdb.d/010-minimal-reference-schema.sql": {
                "source": expected_source("server/src/test/resources/db/phase2/minimal-reference-schema.sql"),
                "rw": False,
            },
            "/docker-entrypoint-initdb.d/020-create-readonly-role.sh": {
                "source": expected_source("infra/phase2/postgres/020-create-readonly-role.sh"),
                "rw": False,
            },
            "/run/secrets/postgres.owner.password": {
                "source": expected_source("infra/phase2/secrets/postgres-owner-password.example"),
                "rw": False,
            },
            "/run/secrets/ti.db.password": {
                "source": expected_source("infra/phase2/secrets/ti-db-password.example"),
                "rw": False,
            },
        },
        "volumes": {
            "/var/lib/postgresql": {
                "name": f"{expected_project}-postgres-data",
                "rw": True,
            },
        },
    },
    "redis": {
        "user": "999:1000",
        "image": "redis:7.4.7-alpine@sha256:02f2cc4882f8bf87c79a220ac958f58c700bdec0dfb9b9ea61b62fb0e8f1bfcf",
        "memory": 256 * 1024 * 1024,
        "pids": 128,
        "tmpfs": {
            "/tmp": "rw,noexec,nosuid,size=32m,uid=999,gid=1000,mode=1770",
        },
        "port_bindings": {},
        "binds": {
            "/run/secrets/ti.redis.password": {
                "source": expected_source("infra/phase2/secrets/ti-redis-password.example"),
                "rw": False,
            },
        },
        "volumes": {
            "/data": {"name": f"{expected_project}-redis-data", "rw": True},
        },
    },
    "api": {
        "user": "10001:10001",
        "image": expected_image,
        "memory": 768 * 1024 * 1024,
        "pids": 256,
        "tmpfs": {
            "/tmp": "rw,noexec,nosuid,size=128m,uid=10001,gid=10001,mode=1770",
        },
        "port_bindings": {
            "8080/tcp": [{"HostIp": "127.0.0.1", "HostPort": api_port}],
        },
        "binds": {
            "/run/secrets/ti.db.password": {
                "source": expected_source("infra/phase2/secrets/ti-db-password.example"),
                "rw": False,
            },
            "/run/secrets/ti.redis.password": {
                "source": expected_source("infra/phase2/secrets/ti-redis-password.example"),
                "rw": False,
            },
            "/run/secrets/ti.login-rate-limit.key-secret": {
                "source": expected_source("infra/phase2/secrets/ti-login-rate-limit-key-secret.example"),
                "rw": False,
            },
        },
        "volumes": {},
    },
}
for service, item in by_service.items():
    host = item["HostConfig"]
    expected = expected_policy[service]
    if item["Config"]["Labels"].get("com.docker.compose.project") != expected_project:
        raise SystemExit(f"unexpected {service} Compose project")
    if host.get("ReadonlyRootfs") is not True:
        raise SystemExit(f"{service} root filesystem is writable")
    if host.get("Privileged") is not False:
        raise SystemExit(f"{service} is privileged")
    if host.get("CapAdd") not in (None, []):
        raise SystemExit(f"{service} adds capabilities: {host.get('CapAdd')}")
    if [value.upper() for value in (host.get("CapDrop") or [])] != ["ALL"]:
        raise SystemExit(f"{service} does not drop all capabilities")
    if host.get("SecurityOpt") != ["no-new-privileges:true"]:
        raise SystemExit(f"unexpected {service} security options: {host.get('SecurityOpt')}")
    if host.get("Init") is not True:
        raise SystemExit(f"{service} lacks init")
    if item["Config"].get("User") != expected["user"]:
        raise SystemExit(f"unexpected {service} user: {item['Config'].get('User')}")
    if item["Config"].get("Image") != expected["image"]:
        raise SystemExit(f"unexpected {service} image: {item['Config'].get('Image')}")
    if host.get("Memory") != expected["memory"]:
        raise SystemExit(f"unexpected {service} memory limit: {host.get('Memory')}")
    if host.get("PidsLimit") != expected["pids"]:
        raise SystemExit(f"unexpected {service} pids limit: {host.get('PidsLimit')}")
    if (host.get("Tmpfs") or {}) != expected["tmpfs"]:
        raise SystemExit(f"unexpected {service} tmpfs: {host.get('Tmpfs')}")
    if (host.get("PortBindings") or {}) != expected["port_bindings"]:
        raise SystemExit(f"unexpected {service} port bindings: {host.get('PortBindings')}")
    if (host.get("RestartPolicy") or {}).get("Name") != "unless-stopped":
        raise SystemExit(f"unexpected {service} restart policy")
    log_config = host.get("LogConfig") or {}
    if log_config.get("Type") != "json-file" or log_config.get("Config") != {
        "max-file": "3", "max-size": "10m"
    }:
        raise SystemExit(f"unexpected {service} logging policy: {log_config}")
    mounts = item.get("Mounts") or []
    unknown_mount_types = {mount.get("Type") for mount in mounts} - {"bind", "volume"}
    if unknown_mount_types:
        raise SystemExit(f"unexpected {service} mount types: {unknown_mount_types}")
    bind_mounts = [mount for mount in mounts if mount.get("Type") == "bind"]
    volume_mounts = [mount for mount in mounts if mount.get("Type") == "volume"]
    for mount_type, selected in (("bind", bind_mounts), ("volume", volume_mounts)):
        destinations = [mount.get("Destination") for mount in selected]
        if None in destinations or len(destinations) != len(set(destinations)):
            raise SystemExit(
                f"duplicate or invalid {service} {mount_type} destinations: {destinations}"
            )
    actual_binds = {
        mount["Destination"]: {
            "source": str(normalize(mount["Source"])),
            "rw": mount.get("RW"),
        }
        for mount in bind_mounts
    }
    actual_volumes = {
        mount["Destination"]: {"name": mount.get("Name"), "rw": mount.get("RW")}
        for mount in volume_mounts
    }
    if actual_binds != expected["binds"]:
        raise SystemExit(f"unexpected {service} bind mounts: {actual_binds}")
    if actual_volumes != expected["volumes"]:
        raise SystemExit(f"unexpected {service} volume mounts: {actual_volumes}")
binds = [
    mount
    for container in containers
    for mount in container.get("Mounts", [])
    if mount.get("Type") == "bind"
]
if len(binds) != 8:
    raise SystemExit(f"expected 8 bind mounts, got {len(binds)}")
if sum(len(policy["binds"]) for policy in expected_policy.values()) != 8:
    raise SystemExit("expected policy does not define exactly 8 bind mounts")
normalized = [normalize(item["Source"]) for item in binds]
if not all(inside(path, copy_root) for path in normalized):
    raise SystemExit(f"bind outside independent copy: {normalized}")
if any(inside(path, source_root) for path in normalized):
    raise SystemExit("canonical source tree was mounted")
PY

docker restart "$PG_CID" "$REDIS_CID" "$API_CID" >/dev/null
recovered=false
for _ in $(seq 1 90); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$API_CID" 2>/dev/null || true)"
    code="$(curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT/readyz" 2>/dev/null || true)"
    if [ "$health" = healthy ] && [ "$code" = 200 ]; then
        recovered=true
        break
    fi
    sleep 2
done
[ "$recovered" = true ]
for service in postgres redis api; do
    container_id="$(compose ps --quiet "$service")"
    [ -n "$container_id" ]
    [ "$(docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' "$container_id")" = 'running/healthy' ]
done
[ "$(curl -sS -o "$WORK/readyz-after-restart.json" -w '%{http_code}' \
    "http://127.0.0.1:$API_PORT/readyz")" = 200 ]
jq -e '.status == "UP"' "$WORK/readyz-after-restart.json" >/dev/null

cleanup_owned_resources

CONTAINER_RESIDUE="$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" | wc -l | tr -d ' ')"
NETWORK_RESIDUE=0
for network in "$PROJECT-backend" "$PROJECT-host-access"; do
    if docker network inspect "$network" >/dev/null 2>&1; then
        NETWORK_RESIDUE=$((NETWORK_RESIDUE + 1))
    fi
done
VOLUME_RESIDUE=0
for volume in "$PROJECT-postgres-data" "$PROJECT-redis-data" "$MAVEN_CACHE"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
        VOLUME_RESIDUE=$((VOLUME_RESIDUE + 1))
    fi
done
IMAGE_RESIDUE=0
if docker image inspect "$IMAGE" >/dev/null 2>&1; then
    IMAGE_RESIDUE=1
fi
[ "$CONTAINER_RESIDUE" -eq 0 ]
[ "$NETWORK_RESIDUE" -eq 0 ]
[ "$VOLUME_RESIDUE" -eq 0 ]
[ "$IMAGE_RESIDUE" -eq 0 ]
assert_port_released "$API_PORT"
assert_port_released "$POSTGRES_PORT"

docker ps -aq | LC_ALL=C sort > "$WORK/final-containers.txt"
docker network ls -q | LC_ALL=C sort > "$WORK/final-networks.txt"
docker volume ls -q | LC_ALL=C sort > "$WORK/final-volumes.txt"
cmp "$BASELINE_CONTAINERS" "$WORK/final-containers.txt"
cmp "$BASELINE_NETWORKS" "$WORK/final-networks.txt"
cmp "$BASELINE_VOLUMES" "$WORK/final-volumes.txt"
verify_docker_client_isolation
verify_acceptance_lock_ownership

FINAL_LIST0="$WORK/controlled-files-final.nul"
capture_controlled_list "$FINAL_LIST0" >/dev/null
cmp "$LIST0" "$FINAL_LIST0"
FINAL_SOURCE_MANIFEST="$WORK/source-manifest-final.json"
FINAL_COPY_MANIFEST="$WORK/copy-manifest-final.json"
FINAL_SOURCE_NONRECURSIVE_MANIFEST="$WORK/source-manifest-final-nonrecursive.json"
FINAL_COPY_NONRECURSIVE_MANIFEST="$WORK/copy-manifest-final-nonrecursive.json"
[ "$(make_manifest "$REPO" "$FINAL_SOURCE_MANIFEST")" -eq "$CONTROLLED_FILE_COUNT" ]
[ "$(make_manifest "$STAGE" "$FINAL_COPY_MANIFEST")" -eq "$CONTROLLED_FILE_COUNT" ]
cmp "$SOURCE_MANIFEST" "$FINAL_SOURCE_MANIFEST"
cmp "$SOURCE_MANIFEST" "$FINAL_COPY_MANIFEST"
[ "$(
    make_manifest "$REPO" "$FINAL_SOURCE_NONRECURSIVE_MANIFEST" "$ACCEPTANCE_CONTROLLED_PATH"
)" -eq "$NONRECURSIVE_FILE_COUNT" ]
[ "$(
    make_manifest "$STAGE" "$FINAL_COPY_NONRECURSIVE_MANIFEST" "$ACCEPTANCE_CONTROLLED_PATH"
)" -eq "$NONRECURSIVE_FILE_COUNT" ]
cmp "$SOURCE_NONRECURSIVE_MANIFEST" "$FINAL_SOURCE_NONRECURSIVE_MANIFEST"
cmp "$SOURCE_NONRECURSIVE_MANIFEST" "$FINAL_COPY_NONRECURSIVE_MANIFEST"

[ -d "$REPORT_ROOT" ] && [ ! -L "$REPORT_ROOT" ]
REPORT_TEMP="$(mktemp "$REPORT_ROOT/.phase4b-category-independent-report.XXXXXX")"
CAPTURED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
jq -n \
    --arg capturedAt "$CAPTURED_AT" \
    --arg manifestSha256 "$MANIFEST_SHA256" \
    --arg nonRecursiveManifestSha256 "$NONRECURSIVE_MANIFEST_SHA256" \
    --arg buildContextSha256 "$SOURCE_BUILD_SHA256" \
    --arg image "$IMAGE" \
    --arg composeProject "$PROJECT" \
    --argjson sourcePythonExplicit "$SOURCE_PYTHON_EXPLICIT" \
    --argjson controlledFileCount "$CONTROLLED_FILE_COUNT" \
    --argjson nonRecursiveFileCount "$NONRECURSIVE_FILE_COUNT" \
    --argjson symlinkCount "$SYMLINK_COUNT" \
    --argjson forbiddenArtifactCount "$FORBIDDEN_ARTIFACT_COUNT" \
    --argjson forbiddenJarCount "$FORBIDDEN_JAR_COUNT" \
    --argjson mavenAttempts "$MAVEN_ATTEMPTS" \
    --argjson mavenMaxAttempts "$MAVEN_MAX_ATTEMPTS" \
    '{
        schemaVersion: 1,
        status: "passed",
        scope: "phase4b-category-prefinal-independent-copy",
        capturedAt: $capturedAt,
        dockerClientIsolation: {
            localUnixDaemonVerified: true,
            explicitDockerHostPinned: true,
            buildxStateIsolated: true,
            isolatedConfigVerifiedAtEnd: true,
            contextMetadataImported: false,
            contextMetadataAbsent: true,
            tlsMaterialImported: false,
            emptyCredentialConfig: true,
            credentialEnvironmentUnset: true,
            remoteBuilderEnvironmentUnset: true,
            callerEndpointOverridesUnset: true,
            callerTlsOverridesUnset: true,
            remoteEndpointRejected: true,
            localUnixSocketVerifiedAtEnd: true,
            phase3DataPlaneUsesPinnedDockerHost: true,
            mavenContainerDockerSocketMatchesPinnedSocket: true,
            allDockerCommandsUseVerifiedLocalUnixSocket: true
        },
        sourceTools: {
            interpreterProvidedExplicitly: $sourcePythonExplicit,
            repositoryLegacyVenv: true,
            legacyDependenciesVerified: true,
            tests: 248,
            failures: 0,
            errors: 0,
            skipped: 0,
            deferredFinalContractAssertionGroups: 1,
            finalContractClosureDeferred: true
        },
        independentCopy: {
            controlledFileCount: $controlledFileCount,
            sourceManifestSha256: $manifestSha256,
            copyManifestSha256: $manifestSha256,
            sourceEqualsCopy: true,
            nonRecursiveManifestExcludedPaths: [
                "docs/refactor/phase4b/personal-bank-category-acceptance.json"
            ],
            nonRecursiveManifestExcludedFileCount: 1,
            nonRecursiveManifestIncludedFileCount: $nonRecursiveFileCount,
            sourceNonRecursiveManifestSha256: $nonRecursiveManifestSha256,
            copyNonRecursiveManifestSha256: $nonRecursiveManifestSha256,
            sourceNonRecursiveEqualsCopy: true,
            dockerCredentialHelperDisabled: true,
            symlinkCount: $symlinkCount,
            forbiddenArtifactCount: $forbiddenArtifactCount,
            forbiddenJarCount: $forbiddenJarCount,
            buildContextSha256: $buildContextSha256,
            phase1Passed: true,
            phase2StaticPassed: true,
            phase3StaticPassed: true,
            phase3TopologyStaticPassed: true,
            miniprogram: {tests: 36, passed: 36, failed: 0},
            dataPlanePassed: true,
            mavenCacheEmptyAtStart: true,
            mavenAttempts: $mavenAttempts,
            mavenMaxAttempts: $mavenMaxAttempts,
            maven: {
                surefire: {tests: 424, failures: 0, errors: 0, skipped: 0},
                failsafe: {tests: 60, failures: 0, errors: 0, skipped: 0}
            },
            image: {uniqueTag: $image, built: true, removed: true},
            compose: {
                uniqueProject: $composeProject,
                healthyServices: 3,
                expectedHealthyServices: 3,
                livezStatus: 200,
                readyzStatus: 200,
                unknownStatus: 401,
                externalMetricsStatus: 404,
                internalMetricsStatus: 200,
                postgresReady: true,
                readOnlyBindCount: 8,
                sourceWorktreeBindCount: 0,
                redisHostBindCount: 0,
                managementHostBindCount: 0,
                apiImageMatchesUniqueTag: true,
                apiUser: "10001:10001",
                readOnlyRootfsServices: 3,
                capDropAllServices: 3,
                noNewPrivilegesServices: 3,
                initServices: 3,
                exactRuntimePolicyServices: 3,
                restartedServices: 3,
                apiRestartRecoveryPassed: true,
                allServicesHealthyAfterRestart: true
            },
            cleanup: {
                containerResidue: 0,
                networkResidue: 0,
                volumeResidue: 0,
                newContainerResidue: 0,
                newNetworkResidue: 0,
                newVolumeResidue: 0,
                deletedBaselineContainerCount: 0,
                deletedBaselineNetworkCount: 0,
                deletedBaselineVolumeCount: 0,
                baselineResourceSetsPreserved: true,
                imageResidue: 0,
                cacheVolumeResidue: 0,
                portResidue: 0
            }
        },
        productionCutover: false
    }' > "$REPORT_TEMP"

jq empty "$REPORT_TEMP"
ln "$REPORT_TEMP" "$REPORT"
REPORT_PUBLISHED=true
rm -f -- "$REPORT_TEMP"
REPORT_TEMP=""

if ! release_acceptance_lock; then
    printf 'Failed to release acceptance lock: %s\n' "$LOCK_DIR" >&2
    rm -f -- "$REPORT"
    exit 1
fi
LOCK_HELD=false

if [ "$KEEP_WORKDIR" != true ]; then
    if ! rm -rf -- "$WORK"; then
        printf 'Failed to remove diagnostic work directory: %s\n' "$WORK" >&2
        rm -f -- "$REPORT"
        exit 1
    fi
    WORK_CLEANED=true
fi

REPORT_SHA256="$(hash_file "$REPORT")"
printf 'Phase 4B category prefinal independent acceptance passed\n'
printf 'report=%s\n' "$REPORT"
printf 'report_sha256=%s\n' "$REPORT_SHA256"
printf 'controlled_file_count=%s\n' "$CONTROLLED_FILE_COUNT"
printf 'manifest_sha256=%s\n' "$MANIFEST_SHA256"
printf 'nonrecursive_manifest_sha256=%s\n' "$NONRECURSIVE_MANIFEST_SHA256"
printf 'build_context_sha256=%s\n' "$SOURCE_BUILD_SHA256"
