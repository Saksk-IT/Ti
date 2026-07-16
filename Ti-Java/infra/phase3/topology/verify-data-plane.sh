#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
RUN_ID="data-gate-$$"
ENV_FILE=$(python3 "$SCRIPT_DIR/prepare_run.py" PREPARE \
    --environment test \
    --run-id "$RUN_ID" \
    --legacy-image "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" \
    --java-image "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb")
RUN_DIR=$(dirname "$ENV_FILE")

cleanup() {
    docker compose --env-file "$ENV_FILE" --file "$SCRIPT_DIR/compose.isolated.yml" \
        --profile runtime down --volumes --remove-orphans >/dev/null 2>&1 || true
    rm -rf -- "$RUN_DIR"
}
trap cleanup EXIT HUP INT TERM

python3 - "$SCRIPT_DIR" "$ENV_FILE" <<'PY'
import pathlib
import sys

script_dir = pathlib.Path(sys.argv[1])
sys.path.insert(0, str(script_dir))

from rehearse_switch import DockerRunner, Direction, SwitchRehearsal
from topology_guard import guard_env_file

topology = guard_env_file(pathlib.Path(sys.argv[2]))
runner = DockerRunner(topology, {})
runner.preflight_local_context()
runner.compose([
    "up", "--detach", "--wait", "--no-build", "--no-deps",
    "legacy-postgres", "legacy-redis", "java-postgres", "java-redis",
])


def values(side):
    prefix = "TI_PHASE3_LEGACY" if side == "legacy" else "TI_PHASE3_JAVA"
    return tuple(topology.values[f"{prefix}_{suffix}"] for suffix in (
        "DB_OWNER", "DB_NAME", "DB_APP", "DB_AUDIT"))


def apply_grants(side):
    owner, database, app_user, audit_user = values(side)
    runner.compose([
        "exec", "-T", f"{side}-postgres", "psql", "--no-psqlrc",
        "--username", owner, "--dbname", database,
        "--set", f"database_name={database}", "--set", f"owner_user={owner}",
        "--set", f"app_user={app_user}", "--set", f"audit_user={audit_user}",
        "--file", "/usr/local/share/grant-after-restore.sql",
    ])


def role_query(side, role_kind, sql, *, check=True):
    owner, database, app_user, audit_user = values(side)
    del owner
    role = app_user if role_kind == "app" else audit_user
    secret_name = "db.app.password" if role_kind == "app" else "db.audit.password"
    return runner.compose([
        "exec", "-T", "-e", f"PGPASSWORD_FILE=/run/secrets/{secret_name}",
        f"{side}-postgres", "sh", "-ec",
        'export PGPASSWORD="$(cat "$PGPASSWORD_FILE")"; '
        'exec psql --no-psqlrc --host 127.0.0.1 --tuples-only --no-align "$@"',
        "phase3-role-probe", "--username", role, "--dbname", database, "--command", sql,
    ], capture=check, check=check)


legacy_owner, legacy_database, _, _ = values("legacy")
runner.compose([
    "exec", "-T", "legacy-postgres", "psql", "--no-psqlrc",
    "--username", legacy_owner, "--dbname", legacy_database,
    "--set", "ON_ERROR_STOP=1", "--command",
    "CREATE TABLE public.phase3_roundtrip (id bigint PRIMARY KEY, note text NOT NULL); "
    "INSERT INTO public.phase3_roundtrip VALUES (1, 'alpha'), (2, E'line\\nvalue'); "
    "CREATE SEQUENCE public.phase3_seq START 9; SELECT nextval('public.phase3_seq');",
])
apply_grants("legacy")
app_state = role_query("legacy", "app", "SHOW default_transaction_read_only;").stdout.strip()
audit_state = role_query("legacy", "audit", "SHOW default_transaction_read_only;").stdout.strip()
if app_state != b"off" or audit_state != b"on":
    raise SystemExit("legacy role boundary mismatch")
role_query("legacy", "app", "INSERT INTO public.phase3_roundtrip VALUES (3, 'app-write');")
audit_write = role_query(
    "legacy", "audit", "INSERT INTO public.phase3_roundtrip VALUES (4, 'forbidden');",
    check=False,
)
if audit_write.returncode == 0:
    raise SystemExit("legacy audit role unexpectedly wrote data")
audit_sequence = role_query(
    "legacy", "audit", "SELECT last_value FROM public.phase3_seq;").stdout.strip()
if audit_sequence != b"9":
    raise SystemExit("legacy audit role could not read sequence state")
audit_sequence_write = role_query(
    "legacy", "audit", "SELECT nextval('public.phase3_seq');", check=False)
if audit_sequence_write.returncode == 0:
    raise SystemExit("legacy audit role unexpectedly advanced a sequence")

direction = Direction("CUTOVER", "legacy", "java", "initial")
rehearsal = SwitchRehearsal(
    topology, direction, runner,
    f"STOP_LEGACY_CAPTURE_RESTORE_JAVA:{topology.run_id}",
)
source_dump = topology.env_file.parent / ".source-roundtrip.dump"
target_dump = topology.env_file.parent / ".target-roundtrip.dump"
try:
    rehearsal._dump_database("legacy", source_dump)
    source_sha = rehearsal._archive_stream_sha256(
        "legacy", source_dump, ["--no-owner", "--no-acl", "--file=-"],
        purpose="verification-source",
    )
    java_owner, java_database, _, _ = values("java")
    rehearsal._restore_archive(
        "java", source_dump, owner=java_owner, database=java_database)
    rehearsal._dump_database("java", target_dump)
    target_sha = rehearsal._archive_stream_sha256(
        "java", target_dump, ["--no-owner", "--no-acl", "--file=-"],
        purpose="verification-target",
    )
    if source_sha != target_sha:
        raise SystemExit("PostgreSQL restore semantic fingerprint mismatch")
finally:
    source_dump.unlink(missing_ok=True)
    target_dump.unlink(missing_ok=True)

apply_grants("java")
java_count = role_query(
    "java", "audit", "SELECT count(*) FROM public.phase3_roundtrip;").stdout.strip()
if java_count != b"3":
    raise SystemExit("restored row count mismatch")
java_sequence = role_query(
    "java", "audit", "SELECT last_value FROM public.phase3_seq;").stdout.strip()
if java_sequence != b"9":
    raise SystemExit("restored audit role could not read sequence state")
for side in ("legacy", "java"):
    redis_size = runner.compose([
        "exec", "-T", f"{side}-redis", "sh", "-ec",
        'export REDISCLI_AUTH="$(cat /run/secrets/redis.password)"; '
        'exec redis-cli --no-auth-warning dbsize',
    ], capture=True).stdout.strip()
    if redis_size != b"0":
        raise SystemExit(f"{side} Redis was not empty")

print("Phase 3 isolated PostgreSQL/Redis roundtrip and role boundaries passed")
PY
