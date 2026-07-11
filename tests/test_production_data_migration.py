"""生产数据迁移目标编排测试。"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
MIGRATOR = ROOT / "scripts/migrate_production_data.sh"


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\n{body}", encoding="utf-8")
    path.chmod(0o755)


@pytest.fixture
def target_environment(tmp_path: Path) -> tuple[Path, dict[str, str], Path]:
    target = tmp_path / "target"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for directory in (
        "var/postgres",
        "var/redis",
        "var/uploads",
        "var/instance",
        "backups",
    ):
        (target / directory).mkdir(parents=True, exist_ok=True)
    (target / "var/postgres/PG_VERSION").write_text("16\n", encoding="utf-8")
    (target / "compose.prod.yml").write_text("services: {}\n", encoding="utf-8")
    (target / ".env.production").write_text(
        "SECRET_KEY=target-secret\n"
        "DEFAULT_ADMIN_USERNAME=admin\n"
        "DEFAULT_ADMIN_PASSWORD=admin-password\n"
        "POSTGRES_USER=studyuser\n"
        "POSTGRES_PASSWORD=target-postgres\n"
        "POSTGRES_DB=ti_db\n"
        "HTTP_PORT=8080\n",
        encoding="utf-8",
    )
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("server1 ssh-ed25519 AAAATEST\n", encoding="utf-8")
    machine_id = tmp_path / "machine-id"
    machine_id.write_text("target-machine\n", encoding="utf-8")
    log = tmp_path / "commands.log"

    write_executable(fake_bin / "id", '[[ "${1:-}" == "-u" ]] && { echo 501; exit 0; }\nexit 1\n')
    write_executable(
        fake_bin / "sudo",
        '[[ "${1:-}" == "-n" && "${2:-}" == "true" ]] && exit 0\n'
        '[[ "${1:-}" == "-n" ]] && shift\nexec "$@"\n',
    )
    write_executable(
        fake_bin / "git",
        'printf "0123456789abcdef0123456789abcdef01234567\\n"\n',
    )
    write_executable(
        fake_bin / "hostname",
        'printf "target2.example\\n"\n',
    )
    write_executable(fake_bin / "curl", 'printf \'curl:%s\\n\' "$*" >> "$MIGRATION_TEST_LOG"\n')
    write_executable(
        fake_bin / "docker",
        r'''printf 'docker:%s\n' "$*" >> "$MIGRATION_TEST_LOG"
case "$*" in
  *"compose "*" config") exit 0 ;;
  *"compose "*" ps --services --filter status=running")
    printf '%s\n' nginx web worker postgres redis backup ;;
  *"compose "*" ps -q web") printf 'web-container\n' ;;
  "inspect --format={{.Image}} web-container") printf 'sha256:web-image-id\n' ;;
  "image inspect --format={{index .RepoDigests 0}} sha256:web-image-id")
    printf 'ghcr.io/saksk-it/ti@sha256:%064d\n' 0 ;;
  *" exec -T postgres postgres --version") printf 'postgres (PostgreSQL) 16.4\n' ;;
  *" exec -T redis redis-server --version")
    printf 'Redis server v=7.2.5 sha=0 malloc=libc bits=64 build=test\n' ;;
  *" exec -T postgres psql -At "*) printf 'f3c4d5e6a7b8\n' ;;
  *) printf 'unexpected docker: %s\n' "$*" >&2; exit 96 ;;
esac
''',
    )
    write_executable(
        fake_bin / "ssh",
        r'''printf 'ssh:%s\n' "$*" >> "$MIGRATION_TEST_LOG"
case "$*" in
  *" mktemp -d /tmp/ti-production-migration.XXXXXX")
    printf '/tmp/ti-production-migration.ABC123\n' ;;
  *" bash /tmp/ti-production-migration.ABC123/export_production_data.sh preflight "*)
    cat <<'EOF'
SOURCE_MACHINE_ID=source-machine
SOURCE_GIT_COMMIT=0123456789abcdef0123456789abcdef01234567
RUNNING_SERVICES=nginx,web,worker,postgres,redis,backup
POSTGRES_MAJOR=16
REDIS_MAJOR=7
WEB_IMAGE_ID=sha256:web-image-id
WEB_IMAGE_DIGEST=ghcr.io/saksk-it/ti@sha256:0000000000000000000000000000000000000000000000000000000000000000
DATA_SIZE_KB=1
AVAILABLE_KB=999999
COMPOSE_SHA256=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
ALEMBIC_VERSION=f3c4d5e6a7b8
UPLOADS_FILE_COUNT=0
INSTANCE_FILE_COUNT=0
EOF
    ;;
  *) exit 0 ;;
esac
''',
    )
    write_executable(fake_bin / "scp", 'printf \'scp:%s\\n\' "$*" >> "$MIGRATION_TEST_LOG"\n')

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "MIGRATION_DOCKER_BIN": str(fake_bin / "docker"),
            "MIGRATION_SUDO_BIN": str(fake_bin / "sudo"),
            "MIGRATION_GIT_BIN": str(fake_bin / "git"),
            "MIGRATION_MACHINE_ID_FILE": str(machine_id),
            "MIGRATION_SSH_BIN": str(fake_bin / "ssh"),
            "MIGRATION_SCP_BIN": str(fake_bin / "scp"),
            "MIGRATION_CURL_BIN": str(fake_bin / "curl"),
            "MIGRATION_TEST_LOG": str(log),
        }
    )
    return target, env, log


def run_migrator(
    target: Path,
    env: dict[str, str],
    known_hosts: Path,
    *extra: str,
    input_text: str | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(MIGRATOR),
            "--source",
            "ubuntu@server1",
            "--source-dir",
            "/opt/ti",
            "--known-hosts",
            str(known_hosts),
            "--target-dir",
            str(target),
            *extra,
        ],
        cwd=ROOT,
        env=env,
        input=input_text,
        text=True,
        capture_output=True,
        check=False,
    )


def test_target_cli_help_documents_all_approved_options() -> None:
    result = subprocess.run(
        ["bash", str(MIGRATOR), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    for option in (
        "--source",
        "--source-dir",
        "--source-port",
        "--identity-file",
        "--known-hosts",
        "--target-dir",
        "--keep-bundle",
        "--dry-run",
    ):
        assert option in result.stdout


def test_target_cli_rejects_unsafe_input_before_ssh(
    target_environment: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    target, env, log = target_environment
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("server1 ssh-ed25519 AAAA\n", encoding="utf-8")
    result = subprocess.run(
        [
            "bash",
            str(MIGRATOR),
            "--source",
            "ubuntu@server1;id",
            "--source-dir",
            "/opt/../root",
            "--source-port",
            "999999",
            "--known-hosts",
            str(known_hosts),
            "--target-dir",
            str(target),
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert not log.exists()


def test_target_preflight_dry_run_uses_strict_ssh_without_mutation(
    target_environment: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    target, env, log = target_environment
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("server1 ssh-ed25519 AAAA\n", encoding="utf-8")
    result = run_migrator(target, env, known_hosts, "--dry-run")

    assert result.returncode == 0, result.stderr
    commands = log.read_text(encoding="utf-8")
    for option in (
        "BatchMode=yes",
        "StrictHostKeyChecking=yes",
        "IdentitiesOnly=yes",
        "UpdateHostKeys=no",
        f"UserKnownHostsFile={known_hosts}",
    ):
        assert option in commands
    assert "scp:" in commands
    assert " preflight " in commands
    assert " prepare " not in commands
    assert " stop " not in commands
    assert "dry-run 预检通过" in result.stderr
    assert not (target / "backups/migrations").exists()


def test_target_confirmation_must_match_both_hosts_before_mutation(
    target_environment: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    target, env, log = target_environment
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("server1 ssh-ed25519 AAAA\n", encoding="utf-8")
    result = run_migrator(target, env, known_hosts, input_text="yes\n")

    assert result.returncode != 0
    commands = log.read_text(encoding="utf-8")
    assert "MIGRATE server1 TO target2.example" in result.stderr
    assert " prepare " not in commands
    assert " stop " not in commands
    assert not (target / "backups/migrations").exists()


def test_target_lock_rejects_concurrent_migration_before_ssh(
    target_environment: tuple[Path, dict[str, str], Path], tmp_path: Path
) -> None:
    target, env, log = target_environment
    known_hosts = tmp_path / "known_hosts"
    known_hosts.write_text("server1 ssh-ed25519 AAAA\n", encoding="utf-8")
    lock = target / "var/.production-data-migration.lock"
    lock.mkdir(mode=0o700)
    (lock / "owner").write_text("another-migration\n", encoding="utf-8")

    result = run_migrator(target, env, known_hosts, "--dry-run")

    assert result.returncode != 0
    assert "迁移锁已存在" in result.stderr
    assert not log.exists()


def test_target_outer_checksum_mismatch_fails_before_extraction(tmp_path: Path) -> None:
    bundle = tmp_path / "migration-test.tar.gz"
    checksum = tmp_path / "migration-test.tar.gz.sha256"
    marker = tmp_path / "tar-called"
    bundle.write_bytes(b"bundle")
    checksum.write_text(f"{'0' * 64}  {bundle.name}\n", encoding="utf-8")
    harness = f'''
source {MIGRATOR!s}
tar() {{ touch {marker!s}; }}
migrator_verify_outer_checksum {bundle!s} {checksum!s}
'''
    result = subprocess.run(
        ["bash", "-c", harness],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "SHA-256 不匹配" in result.stderr
    assert not marker.exists()


def test_target_restore_orders_database_files_migration_and_health(tmp_path: Path) -> None:
    extract = tmp_path / "extract"
    for profile in ("redis", "uploads", "instance"):
        (extract / f"{profile}-extracted" / profile).mkdir(parents=True)
    (extract / "database.dump").write_bytes(b"dump")
    (extract / "database-summary.txt").write_text("users\t42\n", encoding="utf-8")
    (extract / "source.env.production").write_text("SECRET_KEY=source\n", encoding="utf-8")
    (extract / "manifest.txt").write_text(
        "FORMAT_VERSION=1\nREDIS_DBSIZE=3\nUPLOADS_FILE_COUNT=1\n"
        f"UPLOADS_TOTAL_BYTES=6\nUPLOADS_TREE_SHA256={'a' * 64}\n"
        "INSTANCE_FILE_COUNT=1\nINSTANCE_TOTAL_BYTES=6\n"
        f"INSTANCE_TREE_SHA256={'a' * 64}\nALEMBIC_VERSION=f3c4d5e6a7b8\n",
        encoding="utf-8",
    )
    target = tmp_path / "target"
    (target / "var/redis").mkdir(parents=True)
    (target / "var/uploads").mkdir()
    (target / "var/instance").mkdir()
    (target / ".env.production").write_text("POSTGRES_USER=studyuser\nPOSTGRES_DB=ti_db\n")
    log = tmp_path / "restore.log"
    harness = f'''
source {MIGRATOR!s}
MIGRATOR_TARGET_DIR={target!s}
MIGRATOR_SCRIPT_DIR={ROOT / 'scripts'!s}
MIGRATOR_TARGET_MUTATED=0
migrator_validate_and_extract() {{ printf '%s\\n' {extract!s}; }}
migration_read_env_value() {{
  case "$2" in
    POSTGRES_USER) echo studyuser;; POSTGRES_DB) echo ti_db;;
    POSTGRES_PASSWORD) echo target-password;; SECRET_KEY) echo source;;
  esac
}}
migration_root_compose() {{
  printf 'compose:%s\\n' "$*" >> {log!s}
  case "$*" in
    *"redis-cli --raw DBSIZE") echo 3;;
    *"psql -At "*) echo f3c4d5e6a7b8;;
  esac
  return 0
}}
migration_root() {{
  printf 'root:%s\\n' "$*" >> {log!s}
  [[ "$1" == find && "$*" == *" -type f -print"* ]] && echo 1
  return 0
}}
migration_root_docker() {{ echo healthy; }}
migration_database_row_summary() {{ printf 'users\t42\n'; }}
migration_directory_file_stats() {{ printf '1 6 %064d\n' 0 | tr 0 a; }}
migrator_env_value_hash() {{ printf '%064d\n' 0 | tr 0 b; }}
migrator_replace_directory() {{ printf 'replace:%s:%s\\n' "$1" "$2" >> {log!s}; }}
python3() {{ printf 'python:%s\\n' "$*" >> {log!s}; }}
migrator_configure_target() {{ printf 'configure-target\\n' >> {log!s}; }}
migrator_wait_service() {{ printf 'wait:%s\\n' "$1" >> {log!s}; }}
migrator_healthcheck() {{ printf 'health\\n' >> {log!s}; }}
MIGRATOR_TARGET_FACTS='WEB_IMAGE_DIGEST=image@sha256:test'
migrator_local_preflight() {{ echo 'WEB_IMAGE_DIGEST=image@sha256:test'; }}
migrator_restore_bundle ignored ignored source
printf 'mutated=%s\\n' "$MIGRATOR_TARGET_MUTATED"
'''
    result = subprocess.run(
        ["bash", "-c", harness],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    commands = log.read_text(encoding="utf-8")
    expected = (
        "stop backup",
        "stop nginx",
        "stop web worker",
        "stop redis",
        "dropdb --if-exists --force",
        "createdb -U studyuser ti_db",
        "pg_restore --exit-on-error --single-transaction --no-owner --no-privileges",
        "replace:",
        "merge_production_env.py",
        "chown -R redis:redis /data",
        "up -d postgres redis",
        "redis-cli --raw DBSIZE",
        "flask db upgrade",
        "up -d --remove-orphans",
        "health",
    )
    position = -1
    for fragment in expected:
        position = commands.index(fragment, position + 1)
    assert "-e ENSURE_DEFAULT_ADMIN=0 -e RUN_MIGRATIONS=1" in commands
    assert "mutated=1" in result.stdout


def test_target_failure_attempts_target_rollback_and_source_resume_independently(
    tmp_path: Path,
) -> None:
    log = tmp_path / "rollback.log"
    harness = f'''
source {MIGRATOR!s}
MIGRATOR_TARGET_MUTATED=1
MIGRATOR_ROLLBACK_READY=1
MIGRATOR_ROLLBACK_ACTIVE=0
MIGRATOR_FINISHED=0
MIGRATOR_SOURCE_FROZEN=1
MIGRATOR_ROLLBACK_BUNDLE=bundle
MIGRATOR_ROLLBACK_CHECKSUM=checksum
migrator_restore_bundle() {{ echo target-rollback >> {log!s}; return 71; }}
migrator_remote_export() {{ echo source-$1 >> {log!s}; return 72; }}
migrator_cleanup_remote() {{ echo cleanup >> {log!s}; return 0; }}
trap migrator_failure_handler EXIT
false
'''
    result = subprocess.run(
        ["bash", "-c", harness],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert log.read_text(encoding="utf-8").splitlines() == [
        "target-rollback",
        "source-resume",
        "cleanup",
    ]
    assert "自动回滚未完全成功" in result.stderr
    assert "自动恢复未完全成功" in result.stderr


def test_uncertain_finalize_never_rolls_back_target_or_resumes_source(tmp_path: Path) -> None:
    log = tmp_path / "commit.log"
    harness = f'''
source {MIGRATOR!s}
MIGRATOR_TARGET_MUTATED=1
MIGRATOR_ROLLBACK_READY=1
MIGRATOR_FINISHED=0
MIGRATOR_COMMIT_STARTED=1
MIGRATOR_SOURCE_FROZEN=1
MIGRATOR_TARGET_LOCK_HELD=1
migrator_restore_bundle() {{ echo forbidden-rollback >> {log!s}; }}
migrator_remote_export() {{ echo forbidden-resume >> {log!s}; }}
migrator_cleanup_remote() {{ echo cleanup >> {log!s}; }}
migrator_release_target_lock() {{ echo forbidden-unlock >> {log!s}; }}
trap migrator_failure_handler EXIT
false
'''
    result = subprocess.run(
        ["bash", "-c", harness],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert log.read_text(encoding="utf-8").splitlines() == ["cleanup"]
    assert "不回滚服务器 2，也不重启服务器 1" in result.stderr
    assert "保留目标锁" in result.stderr


def test_production_migration_documentation_has_complete_cutover_runbook() -> None:
    guide = (ROOT / "docs/PRODUCTION.md").read_text(encoding="utf-8")

    for required_text in (
        "服务器 2 全新部署",
        "ssh-keyscan",
        "人工核验",
        "--dry-run",
        "migrate_production_data.sh",
        "服务器 1 保持停止",
        "DNS",
        "HTTPS",
        "失败自动回滚",
        "24～72 小时",
    ):
        assert required_text in guide
