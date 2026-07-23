#!/usr/bin/env bash
set -euo pipefail

umask 077
export TZ=UTC
export LC_ALL=C
export LANG=C
export PYTHONDONTWRITEBYTECODE=1
export PYTHONNOUSERSITE=1
export GIT_NO_REPLACE_OBJECTS=1
export GIT_OPTIONAL_LOCKS=0

readonly FIXED_COMMIT="19db389aacad439f63cb93b930bea20ddd31f5e8"
readonly FIXED_PARENT="4c47d1ea220ae9e310338bbf23b74d87d477e20f"
readonly FIXED_ROOT_TREE="76ddb6bfd9a864c350dcdf86303518404227afae"
readonly FIXED_TI_JAVA_TREE="a6c06e505bb3fbd1792ebcc02a78074d306ba830"
readonly FIXED_SERVER_TREE="4743880e2a4bdd6c58c4d274ecdf50fb939c9d06"
readonly FIXED_SRC_MAIN_TREE="9abb4667d87a9433a67d0556dbeac37e10c87dfc"
readonly FIXED_WEB_TREE="a75f69a8205a56843feb055656ddb015ec5b5215"
readonly FIXED_MINIPROGRAM_TREE="9e4f37fe49303329df392dfbe64d2ce9064b7c86"
readonly PARENT_ROOT_TREE="e6ef65c88e87dd73a380f7e7fb095506b9e9b4bd"
readonly PARENT_TI_JAVA_TREE="e214920a30f837aa1760bd4fbc14687f45e9c79d"
readonly PARENT_SERVER_TREE="8deb885bcddbe35485ff67c6a07ded2a77bd3e2e"
readonly PARENT_SRC_MAIN_TREE="bdd88effe149c61fada2300a4ec85bb2a3fdaf1c"
readonly PARENT_WEB_TREE="$FIXED_WEB_TREE"
readonly PARENT_MINIPROGRAM_TREE="$FIXED_MINIPROGRAM_TREE"

readonly EXPECTED_STANDARD_RAW_SHA256="02edc714c98d4ef9cff4f1fdc0a9164e5cdbc8b68ac167fe47f7c107ee307e6c"
readonly EXPECTED_STANDARD_NUMSTAT_SHA256="54aae46c9f36d3959f980434db36aee85088ff8a2c09a7e6abde6d2a1c11cbf8"
readonly EXPECTED_STANDARD_NAME_STATUS_SHA256="dbcdea6367033d145b9e19e2b157004a6b34c662e754fa80916b55373cb64cd7"
readonly EXPECTED_NUL_RAW_SHA256="6186a3200dbc095dc92a93a53128c6c314ee9445a722a85d439eecc7f109c3be"
readonly EXPECTED_NUL_NUMSTAT_SHA256="ed68630f5627c70359d4651276eba4c174117ef292f4716328c383d1fa54b78b"
readonly EXPECTED_NUL_NAME_STATUS_SHA256="1c0b855bbf744b0b8378edecee0cefef257c1bb50d96a0a7bd4c2c1b6a490342"
readonly EXPECTED_RAW_BYTES=10331
readonly EXPECTED_NUMSTAT_BYTES=5175
readonly EXPECTED_NAME_STATUS_BYTES=4996
readonly EXPECTED_CHANGED_PATHS=55
readonly EXPECTED_ADDED_PATHS=18
readonly EXPECTED_MODIFIED_PATHS=37

readonly EXPECTED_TI_JAVA_FILES=1730
readonly EXPECTED_TI_JAVA_MANIFEST_SHA256="46844d1c034ce0d599108dc546de6d2a77af5a8c2609ce84e43ef1b8a84e116c"
readonly EXPECTED_TI_JAVA_ARCHIVE_BYTES=37785600
readonly EXPECTED_TI_JAVA_ARCHIVE_SHA256="7b85ab9f2d863e3c350a3ccf74fda61a19c44f4cfd35b666e35bdef1256164e1"
readonly EXPECTED_MINIPROGRAM_FILES=630
readonly EXPECTED_MINIPROGRAM_MANIFEST_SHA256="770b125807cc7b0c17b8cc996a7016d307cf7554dfa045f34dbd64e3c1c151ef"
readonly EXPECTED_MINIPROGRAM_ARCHIVE_BYTES=10362880
readonly EXPECTED_MINIPROGRAM_ARCHIVE_SHA256="0480cc05c722cf4a5ce673ae2220835cd4fe2614826712b1eea23e1794a02cb8"
readonly EXPECTED_CONTRACT_BYTES=44336
readonly EXPECTED_CONTRACT_SHA256="e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14"
readonly EXPECTED_CONTRACT_PAYLOAD_SHA256="42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4"
readonly EXPECTED_WORM_BYTES=1442
readonly EXPECTED_WORM_SHA256="5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c"
readonly EXPECTED_BUILD_CONTEXT_SHA256="36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7"
readonly EXPECTED_DOCKERFILE_SHA256="bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499"
readonly EXPECTED_SUREFIRE_TESTS=898
readonly EXPECTED_FAILSAFE_TESTS=178
readonly EXPECTED_NODE_D_UNIT_TESTS=31
readonly EXPECTED_NODE_D_EXECUTION_ITS=2
readonly EXPECTED_DOCKER_CLI_PATH="/Applications/Docker.app/Contents/Resources/bin/docker"
readonly EXPECTED_DOCKER_CLI_SHA256="4d2d27ffb3326eaa343a39611d0edfad629f5dc2a7ad8e655ca560e9dddf36c6"
readonly EXPECTED_COMPOSE_PLUGIN_PATH="/Applications/Docker.app/Contents/Resources/cli-plugins/docker-compose"
readonly EXPECTED_COMPOSE_PLUGIN_SHA256="17c88279db5199876ddef60be90dff9b5f69cb7b0fa7f1c04564d30e25a12883"
readonly EXPECTED_BUILDX_PLUGIN_PATH="/Applications/Docker.app/Contents/Resources/cli-plugins/docker-buildx"
readonly EXPECTED_BUILDX_PLUGIN_SHA256="0feb83d47b1738d7d4f701788ac667bbb4c21ae50e903a01e94db3e88bcaf00b"

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)"
LIVE_TI_JAVA="$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd -P)"
REPO="$(CDPATH= cd -- "$LIVE_TI_JAVA/.." && pwd -P)"
readonly SCRIPT_DIR LIVE_TI_JAVA REPO

REPORT=""

usage() {
    printf '%s\n' \
        "Usage: $0 --report TARGET_PATH" \
        "" \
        "Runs the fixed Node D implementation object in an isolated archive copy." \
        "The runner never resolves HEAD, main, origin/main, or copies the live worktree." \
        "TARGET_PATH must be a new direct child of Ti-Java/server/target."
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --report)
            [ "$#" -ge 2 ] || { usage >&2; exit 2; }
            REPORT="$2"
            shift 2
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
[ -n "$REPORT" ] || { usage >&2; exit 2; }

for command_name in docker git tar python3 node curl jq; do
    command -v "$command_name" >/dev/null 2>&1 || {
        printf 'Required command is unavailable: %s\n' "$command_name" >&2
        exit 1
    }
done

[ "${DOCKER_HOST+x}" != x ] \
    && [ "${DOCKER_CONTEXT+x}" != x ] \
    && [ "${DOCKER_CONFIG+x}" != x ] \
    && [ "${DOCKER_AUTH_CONFIG+x}" != x ] \
    && [ "${DOCKER_DEFAULT_PLATFORM+x}" != x ] \
    && [ "${BUILDKIT_HOST+x}" != x ] \
    && [ "${BUILDX_BUILDER+x}" != x ] \
    && [ "${DOCKER_TLS+x}" != x ] \
    && [ "${DOCKER_TLS_VERIFY+x}" != x ] \
    && [ "${DOCKER_CERT_PATH+x}" != x ] || {
    printf '%s\n' \
        'Docker endpoint and TLS environment overrides must be unset for local acceptance' >&2
    exit 1
}

for variable_name in \
    BASH_ENV CDPATH ENV GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG_COUNT \
    GIT_CONFIG_GLOBAL GIT_CONFIG_SYSTEM GIT_DIR GIT_OBJECT_DIRECTORY GIT_WORK_TREE \
    JAVA_TOOL_OPTIONS MAVEN_ARGS MAVEN_OPTS NODE_OPTIONS NODE_PATH \
    PYTHONHOME PYTHONPATH PYTHONSTARTUP PYTHONUSERBASE PYTHONWARNINGS TAR_OPTIONS \
    TESTCONTAINERS_DOCKER_SOCKET_OVERRIDE TESTCONTAINERS_HOST_OVERRIDE \
    TESTCONTAINERS_RYUK_DISABLED _JAVA_OPTIONS \
    CORS_ALLOWED_ORIGINS POSTGRES_DB POSTGRES_USER \
    TI_JAVA_API_MEMORY TI_JAVA_API_PORT TI_JAVA_COMPOSE_PROJECT \
    TI_JAVA_DB_APP_USER TI_JAVA_DB_NAME TI_JAVA_DB_OWNER_PASSWORD_FILE \
    TI_JAVA_DB_OWNER_USER TI_JAVA_DB_PASSWORD_FILE \
    TI_JAVA_LOGIN_RATE_LIMIT_KEY_SECRET_FILE TI_JAVA_LOG_MAX_FILES \
    TI_JAVA_LOG_MAX_SIZE TI_JAVA_PERSONAL_BANK_USER_COUNTS_RATE_LIMIT_KEY_SECRET_FILE \
    TI_JAVA_POSTGRES_MEMORY TI_JAVA_POSTGRES_PORT TI_JAVA_REDIS_MEMORY \
    TI_JAVA_REDIS_PASSWORD_FILE TI_PERSONAL_BANK_USER_COUNTS_READ_RATE_LIMIT_MULTIPLIER \
    TI_PERSONAL_BANK_USER_COUNTS_READ_RATE_LIMIT_NAMESPACE \
    TI_PERSONAL_BANK_USER_COUNTS_READ_REQUESTS_PER_DAY \
    TI_PERSONAL_BANK_USER_COUNTS_READ_REQUESTS_PER_HOUR \
    TI_PERSONAL_BANK_USER_COUNTS_READ_REQUESTS_PER_SECOND TI_RATE_LIMIT_MULTIPLIER \
    TI_SUBJECT_READ_RATE_LIMIT_NAMESPACE TI_SUBJECT_READ_REQUESTS_PER_HOUR \
    TI_SUBJECT_READ_REQUESTS_PER_MINUTE COMPOSE_FILE COMPOSE_PROJECT_NAME \
    COMPOSE_PROFILES COMPOSE_ENV_FILES COMPOSE_PATH_SEPARATOR; do
    if [ "${!variable_name+x}" = x ]; then
        printf 'Caller Compose override must be unset: %s\n' "$variable_name" >&2
        exit 1
    fi
done

REPORT_ROOT="$LIVE_TI_JAVA/server/target"
[ ! -L "$REPORT_ROOT" ] || {
    printf 'Acceptance report root must not be a symlink: %s\n' "$REPORT_ROOT" >&2
    exit 1
}
mkdir -p "$REPORT_ROOT"
[ -d "$REPORT_ROOT" ] && [ ! -L "$REPORT_ROOT" ]
REPORT_ROOT_ID="$(python3 - "$REPORT_ROOT" <<'PY'
import os
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
stat_result = path.stat()
print(f"{stat_result.st_dev}:{stat_result.st_ino}")
PY
)"
REPORT="$(python3 - "$REPORT_ROOT" "$REPORT" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
candidate = pathlib.Path(sys.argv[2])
if not candidate.is_absolute():
    candidate = pathlib.Path.cwd() / candidate
candidate = candidate.resolve(strict=False)
if candidate.parent != root:
    raise SystemExit("acceptance report must be a direct child of Ti-Java/server/target")
if candidate.exists() or candidate.is_symlink():
    raise SystemExit("acceptance report must not already exist")
print(candidate)
PY
)"
readonly REPORT REPORT_ROOT REPORT_ROOT_ID

hash_file() {
    python3 - "$1" <<'PY'
import hashlib
import pathlib
import sys
print(hashlib.sha256(pathlib.Path(sys.argv[1]).read_bytes()).hexdigest())
PY
}

byte_count() {
    python3 - "$1" <<'PY'
import pathlib
import sys
print(len(pathlib.Path(sys.argv[1]).read_bytes()))
PY
}

local_curl() {
    curl -q --noproxy '*' --connect-timeout 5 --max-time 15 "$@"
}

verify_report_root() {
    [ -d "$REPORT_ROOT" ] && [ ! -L "$REPORT_ROOT" ]
    [ "$(python3 - "$REPORT_ROOT" <<'PY'
import pathlib
import sys

stat_result = pathlib.Path(sys.argv[1]).stat()
print(f"{stat_result.st_dev}:{stat_result.st_ino}")
PY
)" = "$REPORT_ROOT_ID" ]
    python3 - "$REPORT_ROOT" "$REPORT" <<'PY'
import pathlib
import sys

root = pathlib.Path(sys.argv[1]).resolve(strict=True)
report = pathlib.Path(sys.argv[2])
if report.parent.resolve(strict=True) != root:
    raise SystemExit("acceptance report parent changed during execution")
if report.exists() or report.is_symlink():
    raise SystemExit("acceptance report appeared during execution")
PY
}

RUNNER_PATH="$SCRIPT_DIR/$(basename "$0")"
[ -f "$RUNNER_PATH" ] && [ ! -L "$RUNNER_PATH" ] || {
    printf 'Acceptance runner must be a regular non-symlink file: %s\n' "$RUNNER_PATH" >&2
    exit 1
}
RUNNER_START_SHA256="$(hash_file "$RUNNER_PATH")"
RUNNER_START_BYTES="$(byte_count "$RUNNER_PATH")"
RUNNER_START_MODE="$(python3 - "$RUNNER_PATH" <<'PY'
import pathlib
import sys
print(f"{pathlib.Path(sys.argv[1]).stat().st_mode & 0o177777:06o}")
PY
)"
[ "$RUNNER_START_MODE" = 100755 ]
readonly RUNNER_PATH RUNNER_START_SHA256 RUNNER_START_BYTES RUNNER_START_MODE

verify_fixed_git_authority() {
    python3 - "$REPO" \
        "$FIXED_COMMIT" "$FIXED_PARENT" "$FIXED_ROOT_TREE" \
        "$FIXED_TI_JAVA_TREE" "$FIXED_SERVER_TREE" "$FIXED_SRC_MAIN_TREE" \
        "$FIXED_WEB_TREE" "$FIXED_MINIPROGRAM_TREE" \
        "$PARENT_ROOT_TREE" "$PARENT_TI_JAVA_TREE" "$PARENT_SERVER_TREE" \
        "$PARENT_SRC_MAIN_TREE" "$PARENT_WEB_TREE" "$PARENT_MINIPROGRAM_TREE" <<'PY'
import pathlib
import subprocess
import sys

(repo, commit, parent, root_tree, ti_tree, server_tree, src_main_tree,
 web_tree, mini_tree, parent_root, parent_ti, parent_server,
 parent_src_main, parent_web, parent_mini) = sys.argv[1:]

def git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", repo, *args], stderr=subprocess.STDOUT
    ).decode("utf-8").strip()

if pathlib.Path(git("rev-parse", "--show-toplevel")).resolve() != pathlib.Path(repo).resolve():
    raise SystemExit("runner is not inside the expected repository")
if git("cat-file", "-t", commit) != "commit" or git("cat-file", "-t", parent) != "commit":
    raise SystemExit("fixed Git authority is not a commit object")
lines = git("cat-file", "-p", commit).splitlines()
if [line for line in lines if line.startswith("tree ")] != [f"tree {root_tree}"]:
    raise SystemExit("fixed commit root tree mismatch")
if [line for line in lines if line.startswith("parent ")] != [f"parent {parent}"]:
    raise SystemExit("fixed commit must have exactly the fixed parent")
parent_lines = git("cat-file", "-p", parent).splitlines()
if [line for line in parent_lines if line.startswith("tree ")] != [f"tree {parent_root}"]:
    raise SystemExit("fixed parent root tree mismatch")
expected = {
    (commit, "Ti-Java"): ti_tree,
    (commit, "Ti-Java/server"): server_tree,
    (commit, "Ti-Java/server/src/main"): src_main_tree,
    (commit, "Ti-Java/web"): web_tree,
    (commit, "miniprogram-1"): mini_tree,
    (parent, "Ti-Java"): parent_ti,
    (parent, "Ti-Java/server"): parent_server,
    (parent, "Ti-Java/server/src/main"): parent_src_main,
    (parent, "Ti-Java/web"): parent_web,
    (parent, "miniprogram-1"): parent_mini,
}
for (revision, path), object_id in expected.items():
    if git("rev-parse", f"{revision}:{path}") != object_id:
        raise SystemExit(f"fixed tree mismatch: {revision}:{path}")

tree_output = subprocess.check_output(
    [
        "git", "-C", repo, "ls-tree", "--full-tree", "-r", "-z", commit,
        "--", "Ti-Java", "miniprogram-1",
    ],
    stderr=subprocess.STDOUT,
)
entries = [entry for entry in tree_output.split(b"\0") if entry]
if len(entries) != 2360:
    raise SystemExit(f"fixed archive Git entry count mismatch: {len(entries)}")
for entry in entries:
    metadata, separator, path = entry.partition(b"\t")
    if not separator:
        raise SystemExit("fixed archive Git entry is malformed")
    mode, object_type, _ = metadata.split(b" ", 2)
    if mode not in {b"100644", b"100755"} or object_type != b"blob":
        raise SystemExit(
            f"fixed archive symlink or submodule is forbidden: "
            f"{mode.decode()} {object_type.decode()} {path.decode()}"
        )
PY
}

make_manifest() {
    root="$1"
    output="$2"
    python3 - "$root" "$output" <<'PY'
import hashlib
import json
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
records = []
for path in sorted(root.rglob("*")):
    if path.is_symlink():
        raise SystemExit(f"fixed archive symlink is forbidden: {path}")
    if not path.is_file():
        continue
    data = path.read_bytes()
    records.append({
        "byteCount": len(data),
        "executable": bool(path.stat().st_mode & stat.S_IXUSR),
        "path": path.relative_to(root).as_posix(),
        "sha256": hashlib.sha256(data).hexdigest(),
    })
payload = (json.dumps(
    records, ensure_ascii=False, sort_keys=True, separators=(",", ":")
) + "\n").encode("utf-8")
pathlib.Path(sys.argv[2]).write_bytes(payload)
print(len(records))
PY
}

verify_manifest_unchanged() {
    root="$1"
    manifest="$2"
    python3 - "$root" "$manifest" <<'PY'
import hashlib
import json
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
records = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
for record in records:
    path = root / record["path"]
    if path.is_symlink() or not path.is_file():
        raise SystemExit(f"fixed archive path changed type: {record['path']}")
    data = path.read_bytes()
    actual = {
        "byteCount": len(data),
        "executable": bool(path.stat().st_mode & stat.S_IXUSR),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    expected = {key: record[key] for key in actual}
    if actual != expected:
        raise SystemExit(f"fixed archive path mutated: {record['path']}")
PY
}

verify_manifest_file_set() {
    root="$1"
    manifest="$2"
    allowed_prefix="${3:-}"
    python3 - "$root" "$manifest" "$allowed_prefix" <<'PY'
import json
import pathlib
import sys

root = pathlib.Path(sys.argv[1])
expected = {
    record["path"]
    for record in json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
}
allowed_prefix = sys.argv[3].strip("/")
actual = set()
for path in root.rglob("*"):
    if path.is_symlink():
        raise SystemExit(f"symlink appeared in fixed copy: {path}")
    if not path.is_file():
        continue
    relative = path.relative_to(root).as_posix()
    if allowed_prefix and (
        relative == allowed_prefix or relative.startswith(allowed_prefix + "/")
    ):
        continue
    actual.add(relative)
if actual != expected:
    missing = sorted(expected - actual)[:10]
    extra = sorted(actual - expected)[:10]
    raise SystemExit(f"fixed copy file set drifted: missing={missing}, extra={extra}")
PY
}

summarize_reports() {
    target="$1"
    output="$2"
    surefire="$3"
    failsafe="$4"
    python3 - "$target" "$output" "$surefire" "$failsafe" <<'PY'
import json
import pathlib
import sys
import xml.etree.ElementTree as ET

target = pathlib.Path(sys.argv[1])
expected = {
    "surefire-reports": int(sys.argv[3]),
    "failsafe-reports": int(sys.argv[4]),
}
summary = {}
for folder, expected_tests in expected.items():
    totals = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
    reports = sorted((target / folder).glob("TEST-*.xml"))
    if not reports:
        raise SystemExit(f"missing Maven XML reports: {folder}")
    for report in reports:
        suite = ET.parse(report).getroot()
        for key in totals:
            totals[key] += int(float(suite.attrib.get(key, "0")))
    required = {"tests": expected_tests, "failures": 0, "errors": 0, "skipped": 0}
    if totals != required:
        raise SystemExit(f"unexpected Maven totals for {folder}: {totals}")
    summary[folder] = totals
pathlib.Path(sys.argv[2]).write_text(
    json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
)
PY
}

verify_node_d_reports() {
    target="$1"
    started_epoch="$2"
    python3 - "$target" "$started_epoch" "$EXPECTED_NODE_D_UNIT_TESTS" \
        "$EXPECTED_NODE_D_EXECUTION_ITS" <<'PY'
import pathlib
import sys
import xml.etree.ElementTree as ET

target = pathlib.Path(sys.argv[1])
started_epoch = int(sys.argv[2])
expected_unit = int(sys.argv[3])
expected_execution = int(sys.argv[4])
unit_classes = {
    "io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationExecutionProtocolStaticTest": 4,
    "io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifierTest": 16,
    "io.saksk.ti.learning.infrastructure.migration.TagMigrationPlanCandidateFactoryTest": 4,
    "io.saksk.ti.architecture.Phase4cTagMigrationExecutionProtocolContractParityTest": 7,
}
it_classes = {
    "io.saksk.ti.learning.infrastructure.migration.Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT": expected_execution,
}
def verify(folder: str, classes: dict[str, int]) -> int:
    total = 0
    for class_name, expected in classes.items():
        path = target / folder / f"TEST-{class_name}.xml"
        if not path.is_file():
            raise SystemExit(f"missing Node D report: {path.name}")
        if path.stat().st_mtime < started_epoch - 1:
            raise SystemExit(f"stale Node D report: {path.name}")
        suite = ET.parse(path).getroot()
        actual = {key: int(float(suite.attrib.get(key, "0"))) for key in (
            "tests", "failures", "errors", "skipped"
        )}
        required = {"tests": expected, "failures": 0, "errors": 0, "skipped": 0}
        if actual != required:
            raise SystemExit(f"unexpected Node D report {path.name}: {actual}")
        total += actual["tests"]
    return total
if verify("surefire-reports", unit_classes) != expected_unit:
    raise SystemExit("Node D unit total mismatch")
if verify("failsafe-reports", it_classes) != expected_execution:
    raise SystemExit("Node D integration total mismatch")
PY
}

pick_port() {
    python3 - <<'PY'
import socket
with socket.socket() as sock:
    sock.bind(("127.0.0.1", 0))
    print(sock.getsockname()[1])
PY
}

verify_fixed_git_authority

STAMP="$(date -u +%Y%m%dT%H%M%SZ)-$$-${RANDOM}"
LOWER_STAMP="$(printf '%s' "$STAMP" | tr '[:upper:]' '[:lower:]')"
WORK="$(mktemp -d "${TMPDIR:-/tmp}/ti-phase4c-noded-independent.XXXXXX")"
STAGE="$WORK/stage"
COPY="$STAGE/Ti-Java"
MINIPROGRAM_COPY="$STAGE/miniprogram-1"
TI_MANIFEST="$WORK/ti-java-manifest.json"
MINI_MANIFEST="$WORK/miniprogram-manifest.json"
TI_ARCHIVE="$WORK/ti-java.tar"
MINI_ARCHIVE="$WORK/miniprogram.tar"
STANDARD_RAW="$WORK/standard.raw"
STANDARD_NUMSTAT="$WORK/standard.numstat"
STANDARD_NAME_STATUS="$WORK/standard.name-status"
NUL_RAW="$WORK/nul.raw"
NUL_NUMSTAT="$WORK/nul.numstat"
NUL_NAME_STATUS="$WORK/nul.name-status"
MAVEN_LOG="$WORK/maven-full.log"
NODE_D_LOG="$WORK/maven-node-c.log"
NODE_LOG="$WORK/miniprogram.log"
DATA_PLANE_LOG="$WORK/data-plane.log"
STATIC_LOG="$WORK/static.log"
RUNTIME_SUMMARY="$WORK/runtime-summary.json"
BASELINE_CONTAINERS="$WORK/baseline-containers.txt"
BASELINE_NETWORKS="$WORK/baseline-networks.txt"
BASELINE_VOLUMES="$WORK/baseline-volumes.txt"
PROJECT="ti-p4c-noded-$LOWER_STAMP"
IMAGE="ti-java-phase4c-noded:$LOWER_STAMP"
MAVEN_CACHE="ti-java-phase4c-noded-m2-$LOWER_STAMP"
OVERRIDE="$WORK/compose.acceptance.yml"
API_PORT=""
POSTGRES_PORT=""
CLEANED=false
REPORT_TEMP=""
REPORT_PUBLISHED=false
PROJECT_OWNED=false
MAVEN_CACHE_OWNED=false
IMAGE_OWNED=false

REAL_DOCKER="$(python3 - "$(command -v docker)" <<'PY'
import pathlib
import sys
print(pathlib.Path(sys.argv[1]).resolve(strict=True))
PY
)"
[ "$REAL_DOCKER" = "$EXPECTED_DOCKER_CLI_PATH" ]
[ "$(hash_file "$REAL_DOCKER")" = "$EXPECTED_DOCKER_CLI_SHA256" ]
[ -f "$EXPECTED_COMPOSE_PLUGIN_PATH" ] && [ ! -L "$EXPECTED_COMPOSE_PLUGIN_PATH" ]
[ -f "$EXPECTED_BUILDX_PLUGIN_PATH" ] && [ ! -L "$EXPECTED_BUILDX_PLUGIN_PATH" ]
[ "$(hash_file "$EXPECTED_COMPOSE_PLUGIN_PATH")" = "$EXPECTED_COMPOSE_PLUGIN_SHA256" ]
[ "$(hash_file "$EXPECTED_BUILDX_PLUGIN_PATH")" = "$EXPECTED_BUILDX_PLUGIN_SHA256" ]
DOCKER_CONFIG="$WORK/docker-config"
BUILDX_CONFIG="$WORK/buildx-config"
DOCKER_WRAPPER_DIR="$WORK/docker-wrapper"
export DOCKER_CONFIG BUILDX_CONFIG

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
    cleanup_failure=0
    docker info >/dev/null 2>&1 || cleanup_failure=1
    if [ "$PROJECT_OWNED" = true ] && [ -f "$OVERRIDE" ] && [ -d "$COPY" ]; then
        compose down --volumes --remove-orphans --timeout 20 >/dev/null 2>&1 \
            || cleanup_failure=1
    fi
    if [ "$PROJECT_OWNED" = true ]; then
        owned="$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT" 2>/dev/null)"
        if [ -n "$owned" ]; then
            for container_id in $owned; do
                docker rm --force "$container_id" >/dev/null 2>&1 || cleanup_failure=1
            done
        fi
        for network in "$PROJECT-backend" "$PROJECT-host-access"; do
            if docker network inspect "$network" >/dev/null 2>&1; then
                docker network rm "$network" >/dev/null 2>&1 || cleanup_failure=1
            fi
        done
        for volume in "$PROJECT-postgres-data" "$PROJECT-redis-data"; do
            if docker volume inspect "$volume" >/dev/null 2>&1; then
                docker volume rm "$volume" >/dev/null 2>&1 || cleanup_failure=1
            fi
        done
    fi
    if [ "$MAVEN_CACHE_OWNED" = true ] \
        && docker volume inspect "$MAVEN_CACHE" >/dev/null 2>&1; then
        docker volume rm "$MAVEN_CACHE" >/dev/null 2>&1 || cleanup_failure=1
    fi
    if [ "$IMAGE_OWNED" = true ] && docker image inspect "$IMAGE" >/dev/null 2>&1; then
        docker image rm "$IMAGE" >/dev/null 2>&1 || cleanup_failure=1
    fi
    if [ "$cleanup_failure" -eq 0 ]; then
        CLEANED=true
    fi
    set -e
    return "$cleanup_failure"
}

on_exit() {
    code=$?
    trap - EXIT HUP INT TERM
    set +e
    if [ "$CLEANED" != true ]; then
        if ! cleanup_owned_resources; then
            printf '%s\n' 'Independent acceptance resource cleanup failed' >&2
            code=1
        fi
    fi
    if [ -n "$REPORT_TEMP" ] && [ -e "$REPORT_TEMP" ]; then
        python3 - "$REPORT_TEMP" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
if path.exists() or path.is_symlink():
    path.unlink()
PY
    fi
    if ! python3 - "$WORK" <<'PY'
import pathlib
import shutil
import sys
path = pathlib.Path(sys.argv[1])
if path.exists():
    shutil.rmtree(path)
PY
    then
        printf '%s\n' 'Independent acceptance work directory cleanup failed' >&2
        code=1
    fi
    if [ "$code" -ne 0 ] && [ "$REPORT_PUBLISHED" = true ] \
        && { [ -e "$REPORT" ] || [ -L "$REPORT" ]; }; then
        python3 - "$REPORT" <<'PY'
import pathlib
import sys
path = pathlib.Path(sys.argv[1])
if path.exists() or path.is_symlink():
    path.unlink()
PY
    fi
    exit "$code"
}
trap on_exit EXIT
trap 'exit 130' HUP INT TERM

assert_port_released() {
    python3 - "$1" <<'PY'
import socket
import sys

port = int(sys.argv[1])
with socket.socket() as sock:
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", port))
PY
}

assert_no_phase3_data_gate_resources() {
    if docker ps --all --format '{{.Label "com.docker.compose.project"}}' \
        | grep -Eq '^ti-phase3-test-data-gate-'; then
        printf '%s\n' 'Pre-existing Phase 3 data-gate Compose project is forbidden' >&2
        return 1
    fi
    if docker network ls --format '{{.Name}}' \
        | grep -Eq '^ti-phase3-test-data-gate-'; then
        printf '%s\n' 'Pre-existing Phase 3 data-gate network is forbidden' >&2
        return 1
    fi
    if docker volume ls --format '{{.Name}}' \
        | grep -Eq '^ti-phase3-test-data-gate-'; then
        printf '%s\n' 'Pre-existing Phase 3 data-gate volume is forbidden' >&2
        return 1
    fi
}

mkdir -p "$STAGE" "$DOCKER_CONFIG/cli-plugins" "$BUILDX_CONFIG" "$DOCKER_WRAPPER_DIR"

python3 - "$DOCKER_CONFIG/config.json" <<'PY'
import json
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_text(
    json.dumps({"auths": {}}, sort_keys=True) + "\n", encoding="utf-8"
)
PY
ln -s "$EXPECTED_COMPOSE_PLUGIN_PATH" "$DOCKER_CONFIG/cli-plugins/docker-compose"
ln -s "$EXPECTED_BUILDX_PLUGIN_PATH" "$DOCKER_CONFIG/cli-plugins/docker-buildx"
SOURCE_DOCKER_CONTEXT="$($REAL_DOCKER context show)"
DOCKER_ENDPOINT="$($REAL_DOCKER context inspect "$SOURCE_DOCKER_CONTEXT" --format '{{(index .Endpoints "docker").Host}}')"
case "$DOCKER_ENDPOINT" in
    unix:///*) ;;
    *) printf '%s\n' 'Local Unix Docker endpoint required' >&2; exit 1 ;;
esac
LOCAL_DOCKER_SOCKET="${DOCKER_ENDPOINT#unix://}"
[ -S "$LOCAL_DOCKER_SOCKET" ] || {
    printf 'Local Docker socket is unavailable: %s\n' "$LOCAL_DOCKER_SOCKET" >&2
    exit 1
}
python3 - "$LOCAL_DOCKER_SOCKET" /var/run/docker.sock <<'PY'
import os
import pathlib
import sys

endpoint = pathlib.Path(sys.argv[1])
nested = pathlib.Path(sys.argv[2])
if not nested.exists() or not nested.is_socket():
    raise SystemExit("nested Maven Docker socket is unavailable")
if not os.path.samefile(endpoint, nested):
    raise SystemExit("nested Maven Docker socket does not match pinned local endpoint")
PY
export DOCKER_HOST="$DOCKER_ENDPOINT"
unset DOCKER_CONTEXT DOCKER_AUTH_CONFIG BUILDKIT_HOST BUILDX_BUILDER
unset DOCKER_TLS DOCKER_TLS_VERIFY DOCKER_CERT_PATH

python3 - "$DOCKER_WRAPPER_DIR/docker" <<'PY'
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_text("""#!/bin/sh
set -eu
if [ "${1:-}" = run ]; then
    shift
    exec "${TI_ACCEPTANCE_REAL_DOCKER:?}" run --env TZ=UTC "$@"
fi
exec "${TI_ACCEPTANCE_REAL_DOCKER:?}" "$@"
""", encoding="utf-8")
PY
chmod 700 "$DOCKER_WRAPPER_DIR/docker"
export TI_ACCEPTANCE_REAL_DOCKER="$REAL_DOCKER"

docker info >/dev/null
docker ps -aq | LC_ALL=C sort > "$BASELINE_CONTAINERS"
docker network ls -q | LC_ALL=C sort > "$BASELINE_NETWORKS"
docker volume ls -q | LC_ALL=C sort > "$BASELINE_VOLUMES"

git -C "$REPO" diff-tree --no-commit-id --raw --abbrev=40 --no-renames -r \
    "$FIXED_COMMIT" > "$STANDARD_RAW"
git -C "$REPO" diff-tree --no-commit-id --numstat --abbrev=40 --no-renames -r \
    "$FIXED_COMMIT" > "$STANDARD_NUMSTAT"
git -C "$REPO" diff-tree --no-commit-id --name-status --abbrev=40 --no-renames -r \
    "$FIXED_COMMIT" > "$STANDARD_NAME_STATUS"
git -C "$REPO" diff-tree --no-commit-id -r --no-renames --raw -z \
    "$FIXED_PARENT" "$FIXED_COMMIT" > "$NUL_RAW"
git -C "$REPO" diff-tree --no-commit-id -r --no-renames --numstat -z \
    "$FIXED_PARENT" "$FIXED_COMMIT" > "$NUL_NUMSTAT"
git -C "$REPO" diff-tree --no-commit-id -r --no-renames --name-status -z \
    "$FIXED_PARENT" "$FIXED_COMMIT" > "$NUL_NAME_STATUS"

[ "$(hash_file "$STANDARD_RAW")" = "$EXPECTED_STANDARD_RAW_SHA256" ]
[ "$(hash_file "$STANDARD_NUMSTAT")" = "$EXPECTED_STANDARD_NUMSTAT_SHA256" ]
[ "$(hash_file "$STANDARD_NAME_STATUS")" = "$EXPECTED_STANDARD_NAME_STATUS_SHA256" ]
[ "$(hash_file "$NUL_RAW")" = "$EXPECTED_NUL_RAW_SHA256" ]
[ "$(hash_file "$NUL_NUMSTAT")" = "$EXPECTED_NUL_NUMSTAT_SHA256" ]
[ "$(hash_file "$NUL_NAME_STATUS")" = "$EXPECTED_NUL_NAME_STATUS_SHA256" ]
[ "$(byte_count "$NUL_RAW")" -eq "$EXPECTED_RAW_BYTES" ]
[ "$(byte_count "$NUL_NUMSTAT")" -eq "$EXPECTED_NUMSTAT_BYTES" ]
[ "$(byte_count "$NUL_NAME_STATUS")" -eq "$EXPECTED_NAME_STATUS_BYTES" ]

python3 - "$NUL_NAME_STATUS" "$EXPECTED_CHANGED_PATHS" \
    "$EXPECTED_ADDED_PATHS" "$EXPECTED_MODIFIED_PATHS" <<'PY'
import collections
import pathlib
import sys
parts = pathlib.Path(sys.argv[1]).read_bytes().split(b"\0")
if not parts or parts[-1] != b"":
    raise SystemExit("name-status delta is not NUL terminated")
parts.pop()
if len(parts) % 2:
    raise SystemExit("name-status delta has an incomplete entry")
entries = [(parts[i].decode(), parts[i + 1].decode()) for i in range(0, len(parts), 2)]
if len(entries) != int(sys.argv[2]):
    raise SystemExit("fixed delta path count mismatch")
counts = collections.Counter(status for status, _ in entries)
if counts != {"A": int(sys.argv[3]), "M": int(sys.argv[4])}:
    raise SystemExit(f"fixed delta status mismatch: {counts}")
if any(not path.startswith("Ti-Java/") for _, path in entries):
    raise SystemExit("fixed delta escaped Ti-Java")
PY

git -C "$REPO" archive --format=tar "$FIXED_COMMIT" -- Ti-Java > "$TI_ARCHIVE"
git -C "$REPO" archive --format=tar "$FIXED_COMMIT" -- miniprogram-1 > "$MINI_ARCHIVE"
[ "$(byte_count "$TI_ARCHIVE")" -eq "$EXPECTED_TI_JAVA_ARCHIVE_BYTES" ]
[ "$(hash_file "$TI_ARCHIVE")" = "$EXPECTED_TI_JAVA_ARCHIVE_SHA256" ]
[ "$(byte_count "$MINI_ARCHIVE")" -eq "$EXPECTED_MINIPROGRAM_ARCHIVE_BYTES" ]
[ "$(hash_file "$MINI_ARCHIVE")" = "$EXPECTED_MINIPROGRAM_ARCHIVE_SHA256" ]
tar -xpf "$TI_ARCHIVE" -C "$STAGE"
tar -xpf "$MINI_ARCHIVE" -C "$STAGE"
[ -d "$COPY" ] && [ -d "$MINIPROGRAM_COPY" ]
[ "$(find "$STAGE" -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')" -eq 2 ]
[ "$(find "$STAGE" -type l | wc -l | tr -d ' ')" -eq 0 ]
python3 - "$STAGE" <<'PY'
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
for path in root.rglob("*"):
    mode = stat.S_IMODE(path.stat().st_mode)
    if path.is_dir():
        if mode != 0o775:
            raise SystemExit(f"fixed archive directory mode drifted: {path}={mode:o}")
    elif path.is_file() and mode not in {0o664, 0o775}:
        raise SystemExit(f"fixed archive file mode drifted: {path}={mode:o}")
PY
python3 - "$STAGE" <<'PY'
import os
import pathlib
import stat
import sys

root = pathlib.Path(sys.argv[1])
for path in root.rglob("*"):
    current = path.stat().st_mode
    if path.is_dir():
        os.chmod(path, 0o755)
    elif path.is_file():
        os.chmod(path, 0o755 if current & stat.S_IXUSR else 0o644)
PY

TI_FILES="$(make_manifest "$COPY" "$TI_MANIFEST")"
MINI_FILES="$(make_manifest "$MINIPROGRAM_COPY" "$MINI_MANIFEST")"
[ "$TI_FILES" -eq "$EXPECTED_TI_JAVA_FILES" ]
[ "$MINI_FILES" -eq "$EXPECTED_MINIPROGRAM_FILES" ]
[ "$(hash_file "$TI_MANIFEST")" = "$EXPECTED_TI_JAVA_MANIFEST_SHA256" ]
[ "$(hash_file "$MINI_MANIFEST")" = "$EXPECTED_MINIPROGRAM_MANIFEST_SHA256" ]
[ "$(byte_count "$COPY/docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-contract.json")" \
    -eq "$EXPECTED_CONTRACT_BYTES" ]
[ "$(hash_file "$COPY/docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-contract.json")" \
    = "$EXPECTED_CONTRACT_SHA256" ]
[ "$(byte_count "$COPY/docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-worm-evidence.json")" \
    -eq "$EXPECTED_WORM_BYTES" ]
[ "$(hash_file "$COPY/docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-worm-evidence.json")" \
    = "$EXPECTED_WORM_SHA256" ]
python3 - "$COPY/docs/refactor/phase4c/personal-bank-tag-migration-execution-protocol-contract.json" \
    "$EXPECTED_CONTRACT_PAYLOAD_SHA256" "$NUL_NAME_STATUS" <<'PY'
import hashlib
import json
import pathlib
import sys

contract_path = pathlib.Path(sys.argv[1])
expected_payload = sys.argv[2]
delta_path = pathlib.Path(sys.argv[3])
document = json.loads(contract_path.read_text(encoding="utf-8"))
payload_document = dict(document)
payload_document.pop("document_payload_sha256", None)
payload = json.dumps(
    payload_document,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
).encode("utf-8")
if hashlib.sha256(payload).hexdigest() != expected_payload:
    raise SystemExit("execution-protocol contract payload digest mismatch")
authority = document["source_authority"]
controls = set(authority["control_sources"])
fixed = set(authority["fixed_non_control_sources"])
if len(controls) != 7 or len(fixed) != 48 or controls & fixed:
    raise SystemExit("execution-protocol 7+48 source partition mismatch")
parts = delta_path.read_bytes().split(b"\0")
if parts[-1] != b"":
    raise SystemExit("fixed delta is not NUL terminated")
paths = {
    parts[index + 1].decode("utf-8").removeprefix("Ti-Java/")
    for index in range(0, len(parts) - 1, 2)
}
if controls | fixed != paths:
    raise SystemExit("execution-protocol 7+48 partition is not the exact D0 delta")
route_state = document["route_state"]
expected_route_state = {
    "migrated_operation_count": 13,
    "pending_operation_count": 598,
    "production_cutover_operation_count": 0,
    "total_operation_count": 611,
    "legacy_flask_remains_production_owner": True,
}
if any(route_state.get(key) != value for key, value in expected_route_state.items()):
    raise SystemExit("execution-protocol route state drifted")
PY
[ "$("$COPY/infra/phase2/hash-java-build-context.sh")" = "$EXPECTED_BUILD_CONTEXT_SHA256" ]
[ "$(hash_file "$COPY/server/Dockerfile")" = "$EXPECTED_DOCKERFILE_SHA256" ]
[ ! -e "$COPY/server/target" ]
[ ! -e "$MINIPROGRAM_COPY/node_modules" ]
FORBIDDEN_ARCHIVE_ARTIFACTS="$(
    find "$STAGE" \
        \( -type d \( -name target -o -name node_modules -o -name .m2 \
            -o -name .venv -o -name __pycache__ -o -name .pytest_cache \) \
        -o -type f \( -name .env -o -name '*.pyc' -o -name '*.class' \) \) \
        -print | wc -l | tr -d ' '
)"
[ "$FORBIDDEN_ARCHIVE_ARTIFACTS" -eq 0 ]

export PYTHONPYCACHEPREFIX="$WORK/python-cache"
(
    cd "$COPY"
    python3 tools/validate_phase1.py
    ./infra/phase2/verify-static.sh
    ./infra/phase3/verify-static.sh
    ./infra/phase3/topology/verify-static.sh
) 2>&1 | tee "$STATIC_LOG"

(
    cd "$MINIPROGRAM_COPY"
    node --test tests/*.test.js
) 2>&1 | tee "$NODE_LOG"
python3 - "$NODE_LOG" <<'PY'
import pathlib
import re
import sys
text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
for pattern in (r"(?:^|\n)[^\n]*tests\s+36(?:\n|$)", r"(?:^|\n)[^\n]*pass\s+36(?:\n|$)", r"(?:^|\n)[^\n]*fail\s+0(?:\n|$)"):
    if not re.search(pattern, text):
        raise SystemExit("fixed miniprogram tests did not report 36/36")
PY

assert_no_phase3_data_gate_resources
(
    cd "$COPY"
    ./infra/phase3/topology/verify-data-plane.sh
) 2>&1 | tee "$DATA_PLANE_LOG"

docker volume inspect "$MAVEN_CACHE" >/dev/null 2>&1 && {
    printf 'Dedicated Maven volume unexpectedly exists: %s\n' "$MAVEN_CACHE" >&2
    exit 1
}
docker volume create "$MAVEN_CACHE" >/dev/null
MAVEN_CACHE_OWNED=true
MAVEN_IMAGE="maven:3.9.16-eclipse-temurin-25@sha256:7e461cec477077c1d9e50b13df8aef9018764410f4c4cd7c34803f10c4c99e4c"
MAVEN_CACHE_FIRST_ENTRY="$(
    PATH="$DOCKER_WRAPPER_DIR:$PATH" docker run --rm \
        --volume "$MAVEN_CACHE:/cache:ro" "$MAVEN_IMAGE" \
        sh -c 'find /cache -mindepth 1 -maxdepth 1 -print -quit'
)"
[ -z "$MAVEN_CACHE_FIRST_ENTRY" ]
PATH="$DOCKER_WRAPPER_DIR:$PATH" docker run --rm "$MAVEN_IMAGE" sh -ec \
    '[ "$TZ" = UTC ] && [ "$(date +%Z)" = UTC ]'

(
    cd "$COPY"
    PATH="$DOCKER_WRAPPER_DIR:$PATH" \
    TI_JAVA_MAVEN_CACHE_VOLUME="$MAVEN_CACHE" \
        ./infra/phase2/verify-in-maven-container.sh clean verify
) 2>&1 | tee "$MAVEN_LOG"
summarize_reports "$COPY/server/target" "$WORK/maven-full-summary.json" \
    "$EXPECTED_SUREFIRE_TESTS" "$EXPECTED_FAILSAFE_TESTS"
grep -Eq '^\[INFO\] Finished at: .*Z$' "$MAVEN_LOG"

FOCUSED_STARTED_EPOCH="$(date +%s)"
python3 - "$COPY/server/target" <<'PY'
import pathlib
import sys

target = pathlib.Path(sys.argv[1])
reports = {
    "surefire-reports": (
        "io.saksk.ti.learning.infrastructure.migration.LegacyPersonalBankTagMigrationExecutionProtocolStaticTest",
        "io.saksk.ti.learning.infrastructure.migration.Ed25519TagMigrationEvidenceVerifierTest",
        "io.saksk.ti.learning.infrastructure.migration.TagMigrationPlanCandidateFactoryTest",
        "io.saksk.ti.architecture.Phase4cTagMigrationExecutionProtocolContractParityTest",
    ),
    "failsafe-reports": (
        "io.saksk.ti.learning.infrastructure.migration.Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT",
    ),
}
for folder, classes in reports.items():
    for class_name in classes:
        path = target / folder / f"TEST-{class_name}.xml"
        if path.exists() or path.is_symlink():
            path.unlink()
        if path.exists() or path.is_symlink():
            raise SystemExit(f"could not remove stale focused report: {path.name}")
PY
(
    cd "$COPY"
    PATH="$DOCKER_WRAPPER_DIR:$PATH" \
    TI_JAVA_MAVEN_CACHE_VOLUME="$MAVEN_CACHE" \
        ./infra/phase2/verify-in-maven-container.sh \
        -Dtest=LegacyPersonalBankTagMigrationExecutionProtocolStaticTest,Ed25519TagMigrationEvidenceVerifierTest,TagMigrationPlanCandidateFactoryTest,Phase4cTagMigrationExecutionProtocolContractParityTest \
        -Dit.test=Phase4cLegacyPersonalBankTagMigrationExecutionProtocolIT \
        verify
) 2>&1 | tee "$NODE_D_LOG"
verify_node_d_reports "$COPY/server/target" "$FOCUSED_STARTED_EPOCH"
grep -Eq '^\[INFO\] Finished at: .*Z$' "$NODE_D_LOG"

docker image inspect "$IMAGE" >/dev/null 2>&1 && {
    printf 'Unique image unexpectedly exists: %s\n' "$IMAGE" >&2
    exit 1
}
docker build --tag "$IMAGE" --file "$COPY/server/Dockerfile" "$COPY/server"
IMAGE_OWNED=true
python3 - "$OVERRIDE" "$IMAGE" <<'PY'
import pathlib
import sys
pathlib.Path(sys.argv[1]).write_text(
    "services:\n  api:\n" + f"    image: {sys.argv[2]}\n" + "    pull_policy: never\n",
    encoding="utf-8",
)
PY

API_PORT="$(pick_port)"
POSTGRES_PORT="$(pick_port)"
while [ "$POSTGRES_PORT" = "$API_PORT" ]; do POSTGRES_PORT="$(pick_port)"; done
export TI_JAVA_COMPOSE_PROJECT="$PROJECT"
export TI_JAVA_API_PORT="$API_PORT"
export TI_JAVA_POSTGRES_PORT="$POSTGRES_PORT"
export TI_SUBJECT_READ_RATE_LIMIT_NAMESPACE="$PROJECT:subject-read-rate"
export TI_PERSONAL_BANK_USER_COUNTS_READ_RATE_LIMIT_NAMESPACE="$PROJECT:user-counts-read-rate"
compose config --quiet
if [ -n "$(docker ps -aq --filter "label=com.docker.compose.project=$PROJECT")" ]; then
    printf 'Unique Compose project unexpectedly owns containers: %s\n' "$PROJECT" >&2
    exit 1
fi
for network in "$PROJECT-backend" "$PROJECT-host-access"; do
    if docker network inspect "$network" >/dev/null 2>&1; then
        printf 'Unique Compose network unexpectedly exists: %s\n' "$network" >&2
        exit 1
    fi
done
for volume in "$PROJECT-postgres-data" "$PROJECT-redis-data"; do
    if docker volume inspect "$volume" >/dev/null 2>&1; then
        printf 'Unique Compose volume unexpectedly exists: %s\n' "$volume" >&2
        exit 1
    fi
done
PROJECT_OWNED=true
compose up --detach --wait --wait-timeout 180 --no-build
[ "$(compose ps --quiet | wc -l | tr -d ' ')" -eq 3 ]
for service in postgres redis api; do
    cid="$(compose ps --quiet "$service")"
    [ "$(docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' "$cid")" = running/healthy ]
done
[ "$(local_curl -sS -o "$WORK/livez.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/livez")" = 200 ]
[ "$(local_curl -sS -o "$WORK/readyz.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/readyz")" = 200 ]
[ "$(local_curl -sS -o "$WORK/unknown.json" -w '%{http_code}' "http://127.0.0.1:$API_PORT/__ti_java_unknown__")" = 401 ]
[ "$(local_curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT/actuator/prometheus")" = 404 ]
jq -e '.status == "UP"' "$WORK/livez.json" >/dev/null
jq -e '.status == "UP"' "$WORK/readyz.json" >/dev/null

PG_CID="$(compose ps --quiet postgres)"
REDIS_CID="$(compose ps --quiet redis)"
API_CID="$(compose ps --quiet api)"

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

docker network inspect "$PROJECT-backend" "$PROJECT-host-access" \
    > "$WORK/runtime-networks.json"
docker inspect "$PG_CID" "$REDIS_CID" "$API_CID" > "$WORK/runtime-inspect.json"
python3 - "$WORK/runtime-inspect.json" "$WORK/runtime-networks.json" \
    "$COPY" "$LIVE_TI_JAVA" "$API_PORT" "$POSTGRES_PORT" "$IMAGE" "$PROJECT" \
    "$RUNTIME_SUMMARY" <<'PY'
import json
import os
import pathlib
import sys

(inspect_path, networks_path, copy_raw, source_raw, api_port, pg_port,
 expected_image, expected_project, summary_path) = sys.argv[1:]
containers = json.loads(pathlib.Path(inspect_path).read_text(encoding="utf-8"))
networks = json.loads(pathlib.Path(networks_path).read_text(encoding="utf-8"))
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

network_policy = {
    f"{expected_project}-backend": True,
    f"{expected_project}-host-access": False,
}
if {item["Name"]: item.get("Internal") for item in networks} != network_policy:
    raise SystemExit("runtime network names or internal policy drifted")
for item in networks:
    labels = item.get("Labels") or {}
    if labels.get("com.docker.compose.project") != expected_project:
        raise SystemExit("runtime network escaped the unique Compose project")

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
        "networks": {f"{expected_project}-backend", f"{expected_project}-host-access"},
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
        "networks": {f"{expected_project}-backend"},
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
        "networks": {f"{expected_project}-backend", f"{expected_project}-host-access"},
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
            "/run/secrets/ti.personal-bank-user-counts-read-rate-limit.key-secret": {
                "source": expected_source("infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example"),
                "rw": False,
            },
        },
        "volumes": {},
    },
}

secret_values = {
    (copy_root / relative).read_text(encoding="utf-8").strip()
    for relative in (
        "infra/phase2/secrets/postgres-owner-password.example",
        "infra/phase2/secrets/ti-db-password.example",
        "infra/phase2/secrets/ti-redis-password.example",
        "infra/phase2/secrets/ti-login-rate-limit-key-secret.example",
        "infra/phase2/secrets/ti-personal-bank-user-counts-rate-limit-key-secret.example",
    )
}
if "" in secret_values:
    raise SystemExit("empty example secret is forbidden")

all_binds = []
for service, item in by_service.items():
    host = item["HostConfig"]
    expected = expected_policy[service]
    labels = item["Config"].get("Labels") or {}
    if labels.get("com.docker.compose.project") != expected_project:
        raise SystemExit(f"unexpected {service} Compose project")
    if host.get("ReadonlyRootfs") is not True or host.get("Privileged") is not False:
        raise SystemExit(f"unsafe {service} rootfs or privileged policy")
    if host.get("CapAdd") not in (None, []):
        raise SystemExit(f"{service} adds capabilities")
    if [value.upper() for value in (host.get("CapDrop") or [])] != ["ALL"]:
        raise SystemExit(f"{service} does not drop all capabilities")
    if host.get("SecurityOpt") != ["no-new-privileges:true"] or host.get("Init") is not True:
        raise SystemExit(f"unexpected {service} security/init policy")
    if item["Config"].get("User") != expected["user"]:
        raise SystemExit(f"unexpected {service} user")
    if item["Config"].get("Image") != expected["image"]:
        raise SystemExit(f"unexpected {service} image")
    if host.get("Memory") != expected["memory"] or host.get("PidsLimit") != expected["pids"]:
        raise SystemExit(f"unexpected {service} resource limits")
    if (host.get("Tmpfs") or {}) != expected["tmpfs"]:
        raise SystemExit(f"unexpected {service} tmpfs")
    if (host.get("PortBindings") or {}) != expected["port_bindings"]:
        raise SystemExit(f"unexpected {service} port bindings")
    if set((item.get("NetworkSettings", {}).get("Networks") or {})) != expected["networks"]:
        raise SystemExit(f"unexpected {service} runtime networks")
    if (host.get("RestartPolicy") or {}).get("Name") != "unless-stopped":
        raise SystemExit(f"unexpected {service} restart policy")
    log_config = host.get("LogConfig") or {}
    if log_config.get("Type") != "json-file" or log_config.get("Config") != {
        "max-file": "3", "max-size": "10m"
    }:
        raise SystemExit(f"unexpected {service} logging policy")
    environment = item["Config"].get("Env") or []
    if any(secret in value for secret in secret_values for value in environment):
        raise SystemExit(f"raw secret value escaped into {service} environment")
    mounts = item.get("Mounts") or []
    if {mount.get("Type") for mount in mounts} - {"bind", "volume"}:
        raise SystemExit(f"unexpected {service} mount type")
    bind_mounts = [mount for mount in mounts if mount.get("Type") == "bind"]
    volume_mounts = [mount for mount in mounts if mount.get("Type") == "volume"]
    for selected in (bind_mounts, volume_mounts):
        destinations = [mount.get("Destination") for mount in selected]
        if None in destinations or len(destinations) != len(set(destinations)):
            raise SystemExit(f"duplicate or invalid {service} mount destination")
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
        raise SystemExit(f"unexpected {service} bind mounts")
    if actual_volumes != expected["volumes"]:
        raise SystemExit(f"unexpected {service} volume mounts")
    all_binds.extend(bind_mounts)

if len(all_binds) != 9 or any(mount.get("RW") is not False for mount in all_binds):
    raise SystemExit(f"expected exactly 9 read-only binds, got {len(all_binds)}")
normalized_sources = [normalize(mount["Source"]) for mount in all_binds]
if len(set(normalized_sources)) != 7:
    raise SystemExit("expected exactly 7 unique bind sources")
if not all(inside(path, copy_root) for path in normalized_sources):
    raise SystemExit("runtime bind escaped fixed independent copy")
if any(inside(path, source_root) for path in normalized_sources):
    raise SystemExit("live Ti-Java worktree was mounted")

summary = {
    "serviceCount": 3,
    "readOnlyBindCount": 9,
    "uniqueBindSourceCount": 7,
    "sourceWorktreeBindCount": 0,
    "environmentSecretValueCount": 0,
    "readOnlyRootfsServiceCount": 3,
    "capDropAllServiceCount": 3,
    "noNewPrivilegesServiceCount": 3,
    "initServiceCount": 3,
    "exactRuntimePolicyServiceCount": 3,
}
pathlib.Path(summary_path).write_text(
    json.dumps(summary, sort_keys=True) + "\n", encoding="utf-8"
)
PY

docker restart "$PG_CID" "$REDIS_CID" "$API_CID" >/dev/null
recovered=false
for _ in $(seq 1 90); do
    health="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$API_CID" 2>/dev/null || true)"
    code="$(local_curl -sS -o /dev/null -w '%{http_code}' "http://127.0.0.1:$API_PORT/readyz" 2>/dev/null || true)"
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
    [ "$(docker inspect --format '{{.State.Status}}/{{.State.Health.Status}}' "$container_id")" = running/healthy ]
done
[ "$(local_curl -sS -o "$WORK/readyz-after-restart.json" -w '%{http_code}' \
    "http://127.0.0.1:$API_PORT/readyz")" = 200 ]
jq -e '.status == "UP"' "$WORK/readyz-after-restart.json" >/dev/null
docker exec "$PG_CID" pg_isready --quiet \
    --username ti_java_fixture_owner \
    --dbname ti_java_phase2
docker exec "$API_CID" bash -ec '
exec 3<>/dev/tcp/127.0.0.1/9090
printf "GET /actuator/prometheus HTTP/1.0\r\nHost: localhost\r\nConnection: close\r\n\r\n" >&3
cat <&3
' > "$WORK/internal-metrics-after-restart.http"
tr -d '\r' < "$WORK/internal-metrics-after-restart.http" \
    > "$WORK/internal-metrics-after-restart.normalized"
grep -q '^HTTP/1.1 200' "$WORK/internal-metrics-after-restart.normalized"
grep -q '^jvm_info' "$WORK/internal-metrics-after-restart.normalized"

verify_manifest_unchanged "$COPY" "$TI_MANIFEST"
verify_manifest_unchanged "$MINIPROGRAM_COPY" "$MINI_MANIFEST"
verify_manifest_file_set "$COPY" "$TI_MANIFEST" server/target
verify_manifest_file_set "$MINIPROGRAM_COPY" "$MINI_MANIFEST"
[ "$("$COPY/infra/phase2/hash-java-build-context.sh")" = "$EXPECTED_BUILD_CONTEXT_SHA256" ]

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
if docker image inspect "$IMAGE" >/dev/null 2>&1; then IMAGE_RESIDUE=1; fi
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
python3 - "$DOCKER_CONFIG/config.json" <<'PY'
import json
import pathlib
import sys
if json.loads(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")) != {"auths": {}}:
    raise SystemExit("isolated Docker credential config mutated")
PY
[ -S "$LOCAL_DOCKER_SOCKET" ]
[ -L "$DOCKER_CONFIG/cli-plugins/docker-compose" ]
[ -L "$DOCKER_CONFIG/cli-plugins/docker-buildx" ]
[ "$(readlink "$DOCKER_CONFIG/cli-plugins/docker-compose")" = "$EXPECTED_COMPOSE_PLUGIN_PATH" ]
[ "$(readlink "$DOCKER_CONFIG/cli-plugins/docker-buildx")" = "$EXPECTED_BUILDX_PLUGIN_PATH" ]
[ "$(hash_file "$REAL_DOCKER")" = "$EXPECTED_DOCKER_CLI_SHA256" ]
[ "$(hash_file "$EXPECTED_COMPOSE_PLUGIN_PATH")" = "$EXPECTED_COMPOSE_PLUGIN_SHA256" ]
[ "$(hash_file "$EXPECTED_BUILDX_PLUGIN_PATH")" = "$EXPECTED_BUILDX_PLUGIN_SHA256" ]

RUNNER_END_SHA256="$(hash_file "$RUNNER_PATH")"
RUNNER_END_BYTES="$(byte_count "$RUNNER_PATH")"
RUNNER_END_MODE="$(python3 - "$RUNNER_PATH" <<'PY'
import pathlib
import sys
print(f"{pathlib.Path(sys.argv[1]).stat().st_mode & 0o177777:06o}")
PY
)"
[ "$RUNNER_END_SHA256" = "$RUNNER_START_SHA256" ]
[ "$RUNNER_END_BYTES" = "$RUNNER_START_BYTES" ]
[ "$RUNNER_END_MODE" = "$RUNNER_START_MODE" ]
RUNNER_SHA256="$RUNNER_START_SHA256"
RUNNER_BYTES="$RUNNER_START_BYTES"
REPORT_RELATIVE="server/target/$(basename "$REPORT")"
verify_report_root
REPORT_TEMP="$(mktemp "$REPORT_ROOT/.phase4c-noded-independent-report.XXXXXX")"
CAPTURED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
python3 - "$REPORT_TEMP" "$CAPTURED_AT" "$RUNNER_SHA256" "$RUNNER_BYTES" \
    "$REPORT_RELATIVE" "$PROJECT" "$IMAGE" "$STATIC_LOG" "$NODE_LOG" \
    "$DATA_PLANE_LOG" "$MAVEN_LOG" "$NODE_D_LOG" "$RUNTIME_SUMMARY" <<'PY'
import hashlib
import json
import pathlib
import sys

(output_raw, captured_at, runner_sha, runner_bytes, report_relative,
 project, image, static_log, node_log, data_plane_log, maven_log,
 node_d_log, runtime_summary) = sys.argv[1:]

def artifact(path_raw):
    path = pathlib.Path(path_raw)
    data = path.read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "byteCount": len(data)}

document = {
    "schemaVersion": 1,
    "evidenceId": "ti.phase4c.tag-migration-execution-protocol-independent-acceptance.raw-v1",
    "status": "passed",
    "scope": "phase4c-learning-tag-migration-execution-protocol-fixed-d0-independent-copy",
    "capturedAt": captured_at,
    "authority": {
        "objectFormat": "sha1",
        "commitOid": "19db389aacad439f63cb93b930bea20ddd31f5e8",
        "parentOid": "4c47d1ea220ae9e310338bbf23b74d87d477e20f",
        "rootTreeOid": "76ddb6bfd9a864c350dcdf86303518404227afae",
        "parentRootTreeOid": "e6ef65c88e87dd73a380f7e7fb095506b9e9b4bd",
        "tiJavaTreeOid": "a6c06e505bb3fbd1792ebcc02a78074d306ba830",
        "parentTiJavaTreeOid": "e214920a30f837aa1760bd4fbc14687f45e9c79d",
        "serverTreeOid": "4743880e2a4bdd6c58c4d274ecdf50fb939c9d06",
        "parentServerTreeOid": "8deb885bcddbe35485ff67c6a07ded2a77bd3e2e",
        "serverSrcMainTreeOid": "9abb4667d87a9433a67d0556dbeac37e10c87dfc",
        "parentServerSrcMainTreeOid": "bdd88effe149c61fada2300a4ec85bb2a3fdaf1c",
        "webTreeOid": "a75f69a8205a56843feb055656ddb015ec5b5215",
        "parentWebTreeOid": "a75f69a8205a56843feb055656ddb015ec5b5215",
        "miniprogramTreeOid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
        "parentMiniprogramTreeOid": "9e4f37fe49303329df392dfbe64d2ce9064b7c86",
        "changedPathCount": 55,
        "addedPathCount": 18,
        "modifiedPathCount": 37,
        "deletedPathCount": 0,
        "controlSourceCount": 7,
        "fixedNonControlSourceCount": 48,
        "standardRawSha256": "02edc714c98d4ef9cff4f1fdc0a9164e5cdbc8b68ac167fe47f7c107ee307e6c",
        "standardNumstatSha256": "54aae46c9f36d3959f980434db36aee85088ff8a2c09a7e6abde6d2a1c11cbf8",
        "standardNameStatusSha256": "dbcdea6367033d145b9e19e2b157004a6b34c662e754fa80916b55373cb64cd7",
        "nulRawSha256": "6186a3200dbc095dc92a93a53128c6c314ee9445a722a85d439eecc7f109c3be",
        "nulNumstatSha256": "ed68630f5627c70359d4651276eba4c174117ef292f4716328c383d1fa54b78b",
        "nulNameStatusSha256": "1c0b855bbf744b0b8378edecee0cefef257c1bb50d96a0a7bd4c2c1b6a490342",
    },
    "runner": {
        "path": "tools/run_phase4c_tag_migration_execution_protocol_independent_acceptance.sh",
        "sha256": runner_sha,
        "byteCount": int(runner_bytes),
        "mode": "100755",
        "rawReportPath": report_relative,
    },
    "fixedArchive": {
        "gitArchiveOnly": True,
        "gitModesNormalizedForExecution": True,
        "liveWorktreeCopied": False,
        "liveRefResolved": False,
        "tiJava": {
            "fileCount": 1730,
            "archiveByteCount": 37785600,
            "archiveSha256": "7b85ab9f2d863e3c350a3ccf74fda61a19c44f4cfd35b666e35bdef1256164e1",
            "manifestSha256": "46844d1c034ce0d599108dc546de6d2a77af5a8c2609ce84e43ef1b8a84e116c",
        },
        "miniprogram": {
            "fileCount": 630,
            "archiveByteCount": 10362880,
            "archiveSha256": "0480cc05c722cf4a5ce673ae2220835cd4fe2614826712b1eea23e1794a02cb8",
            "manifestSha256": "770b125807cc7b0c17b8cc996a7016d307cf7554dfa045f34dbd64e3c1c151ef",
        },
        "symlinkOrSubmoduleCount": 0,
        "forbiddenArtifactCount": 0,
        "trackedFilesUnchangedAfterVerification": True,
        "unexpectedFilesOutsideServerTarget": 0,
        "contract": {
            "sha256": "e236b3cde251026c3a189762b650eb4df80213dcdab667a5b8f50eb20a0e8e14",
            "payloadSha256": "42599261bc5632feed89fc41637ee1a98cff844dd9dc776f889d155a0567a7c4",
            "byteCount": 44336,
        },
        "worm": {
            "sha256": "5c3fe0f9d7cba79fca6c2351d811924346182cf61e06b730a0eeb0bcef50081c",
            "byteCount": 1442,
        },
        "buildContextSha256": "36978a808a327abfb3c7b3dfe138f5622000213a25bad762b59128c78894d7c7",
        "dockerfileSha256": "bb99afb7264a3a0d64b2e76d07a663bfe4a08cacca0387dff07635818a1ef499",
    },
    "verification": {
        "phase1Passed": True,
        "phase2StaticPassed": True,
        "phase3StaticPassed": True,
        "phase3TopologyStaticPassed": True,
        "miniprogram": {"tests": 36, "passed": 36, "failed": 0},
        "topologyDataPlanePassed": True,
        "mavenCacheEmptyAtStart": True,
        "timezone": "UTC",
        "maven": {
            "surefire": {"tests": 898, "failures": 0, "errors": 0, "skipped": 0},
            "failsafe": {"tests": 178, "failures": 0, "errors": 0, "skipped": 0},
        },
        "focusedNodeD": {
            "unit": {"tests": 31, "failures": 0, "errors": 0, "skipped": 0},
            "executionProtocolIntegration": {
                "tests": 2,
                "failures": 0,
                "errors": 0,
                "skipped": 0,
            },
        },
        "logs": {
            "static": artifact(static_log),
            "miniprogram": artifact(node_log),
            "topologyDataPlane": artifact(data_plane_log),
            "mavenFull": artifact(maven_log),
            "mavenFocusedNodeD": artifact(node_d_log),
        },
        "sourceDiscovery": {
            "executedInsideIndependentCopy": False,
            "claimedIndependentCopyTestCount": 0,
            "reason": "legacy frozen-source dependencies live outside the fixed Ti-Java archive",
        },
        "image": {"uniqueTag": image, "built": True, "removed": True},
    },
    "runtimeIsolation": {
        "hostTrustBoundary": {
            "trustedLocalHostKernelAndShell": True,
            "trustedHostGitTarPythonNodeCurlAndJq": True,
            "adversarialConcurrentDockerDaemonActorExcluded": True,
            "phase3DataGatePreexistingResourcePrefixRejected": True,
        },
        "docker": {
            "localUnixDaemonVerified": True,
            "nestedMavenSocketMatchesPinnedSocket": True,
            "isolatedCredentialConfig": True,
            "callerEndpointOverridesUnset": True,
            "callerTlsOverridesUnset": True,
            "buildxStateIsolated": True,
            "dockerCliPath": "/Applications/Docker.app/Contents/Resources/bin/docker",
            "dockerCliSha256": "4d2d27ffb3326eaa343a39611d0edfad629f5dc2a7ad8e655ca560e9dddf36c6",
            "composePluginSha256": "17c88279db5199876ddef60be90dff9b5f69cb7b0fa7f1c04564d30e25a12883",
            "buildxPluginSha256": "0feb83d47b1738d7d4f701788ac667bbb4c21ae50e903a01e94db3e88bcaf00b",
        },
        "compose": {
            "uniqueProject": project,
            "healthyServiceCount": 3,
            "livezStatus": 200,
            "readyzStatus": 200,
            "unknownStatus": 401,
            "externalMetricsStatus": 404,
            "internalMetricsStatus": 200,
            "postgresReady": True,
            **json.loads(pathlib.Path(runtime_summary).read_text(encoding="utf-8")),
            "restartedServiceCount": 3,
            "apiRestartRecoveryPassed": True,
            "allServicesHealthyAfterRestart": True,
            "postgresReadyAfterRestart": True,
            "internalMetricsAfterRestartStatus": 200,
        },
        "cleanup": {
            "containerResidue": 0,
            "networkResidue": 0,
            "volumeResidue": 0,
            "imageResidue": 0,
            "cacheVolumeResidue": 0,
            "portResidue": 0,
            "baselineContainerSetPreserved": True,
            "baselineNetworkSetPreserved": True,
            "baselineVolumeSetPreserved": True,
            "daemonImageSetPreservationClaimed": False,
            "daemonBuildCachePreservationClaimed": False,
        },
    },
    "productionBoundary": {
        "productionCredentialsRead": False,
        "productionDataReadOrMutated": False,
        "productionDatabaseConnected": False,
        "productionOperatorExecuted": False,
        "productionComposeReadOrMutated": False,
        "realMigrationExecution": False,
        "legacyRuntimeDisabled": False,
        "gatewayOrProxyChanged": False,
        "productionCutover": False,
    },
    "routeState": {
        "migratedOperationCount": 13,
        "pendingOperationCount": 598,
        "productionCutoverOperationCount": 0,
    },
    "closure": {
        "fixedD0IndependentCopyAcceptanceClosed": True,
        "provesOnlyCommit": "19db389aacad439f63cb93b930bea20ddd31f5e8",
        "provesD1EvidenceCommit": False,
        "provesD2AnchorCommit": False,
        "executionProtocolControlSourcesExternalGitAnchorComplete": False,
    },
}
pathlib.Path(output_raw).write_text(
    json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
PY
jq empty "$REPORT_TEMP"
verify_report_root
ln "$REPORT_TEMP" "$REPORT"
REPORT_PUBLISHED=true
python3 - "$REPORT_TEMP" <<'PY'
import pathlib
import sys
pathlib.Path(sys.argv[1]).unlink()
PY
REPORT_TEMP=""

REPORT_SHA256="$(hash_file "$REPORT")"
REPORT_BYTES="$(byte_count "$REPORT")"
python3 - "$WORK" <<'PY'
import pathlib
import shutil
import sys

path = pathlib.Path(sys.argv[1])
if path.exists():
    shutil.rmtree(path)
PY
printf '%s\n' 'Phase 4C tag-migration execution-protocol independent acceptance passed'
printf 'fixed_commit=%s\n' "$FIXED_COMMIT"
printf 'report=%s\n' "$REPORT"
printf 'report_sha256=%s\n' "$REPORT_SHA256"
printf 'report_bytes=%s\n' "$REPORT_BYTES"
