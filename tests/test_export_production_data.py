"""源服务器生产数据导出状态机测试。"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "scripts/export_production_data.sh"
ARCHIVE_VALIDATOR = ROOT / "scripts/lib/validate_migration_archive.py"


def write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\n{body}", encoding="utf-8")
    path.chmod(0o755)


@dataclass(frozen=True)
class ExportEnvironment:
    source: Path
    env: dict[str, str]
    log: Path
    migration_id: str = "20260711T120000Z-test"

    @property
    def workspace(self) -> Path:
        return self.source / "backups/migrations" / self.migration_id

    @property
    def state(self) -> Path:
        return self.workspace / "state"

    @property
    def lock(self) -> Path:
        return self.source / "var/.production-migration.lock"

    def run(self, action: str, **extra_env: str) -> subprocess.CompletedProcess[str]:
        env = {**self.env, **extra_env}
        return subprocess.run(
            [
                "bash",
                str(EXPORTER),
                action,
                "--source-dir",
                str(self.source),
                "--migration-id",
                self.migration_id,
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )


@pytest.fixture
def export_environment(tmp_path: Path) -> ExportEnvironment:
    source = tmp_path / "source"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    for directory in (
        "var/postgres",
        "var/redis/appendonlydir",
        "var/uploads/nested",
        "var/instance",
        "backups/migrations",
    ):
        (source / directory).mkdir(parents=True, exist_ok=True)
    (source / "var/redis/dump.rdb").write_bytes(b"redis-rdb")
    (source / "var/redis/appendonlydir/appendonly.aof").write_bytes(b"redis-aof")
    (source / "var/uploads/nested/upload.txt").write_text("upload", encoding="utf-8")
    (source / "var/instance/app.db").write_bytes(b"instance")
    (source / "var/postgres/PG_VERSION").write_text("16\n", encoding="utf-8")
    (source / "compose.prod.yml").write_text("services: {}\n", encoding="utf-8")
    (source / ".env.production").write_text(
        "POSTGRES_USER=studyuser\n"
        "POSTGRES_PASSWORD=pg-password-must-not-leak\n"
        "POSTGRES_DB=ti_db\n"
        "SECRET_KEY=secret-value-must-not-leak\n"
        "AI_CHANGE_RECORD_TOKEN=token-value-must-not-leak\n",
        encoding="utf-8",
    )
    machine_id = tmp_path / "machine-id"
    machine_id.write_text("source-machine-id\n", encoding="utf-8")
    log = tmp_path / "commands.log"

    write_executable(fake_bin / "id", '[[ "${1:-}" == "-u" ]] && { echo 501; exit 0; }\nexit 1\n')
    write_executable(
        fake_bin / "sudo",
        '[[ "${1:-}" == "-n" && "${2:-}" == "true" ]] && exit 0\n'
        '[[ "${1:-}" == "-n" ]] && shift\nexec "$@"\n',
    )
    write_executable(
        fake_bin / "git",
        '[[ "${1:-}" == "-C" ]] || exit 2\nprintf "0123456789abcdef0123456789abcdef01234567\\n"\n',
    )
    write_executable(
        fake_bin / "docker",
        r'''printf '%s\n' "$*" >> "$MIGRATION_FAKE_LOG"
if [[ -n "${MIGRATION_FAKE_FAIL_MATCH:-}" && "$*" == *"$MIGRATION_FAKE_FAIL_MATCH"* ]]; then
  exit 73
fi
case "$*" in
  *"compose "*" config") exit 0 ;;
  *"compose "*" ps --services --filter status=running web worker nginx backup")
    printf '%s' "${MIGRATION_FAKE_RUNNING_WRITERS:-}"
    ;;
  *"compose "*" ps --services --filter status=running")
    printf '%s\n' ${MIGRATION_FAKE_RUNNING_SERVICES:-nginx web worker postgres redis backup}
    ;;
  *"compose "*" ps -q web") printf 'web-container\n' ;;
  "inspect --format={{.Image}} web-container") printf 'sha256:web-image-id\n' ;;
  "image inspect --format={{index .RepoDigests 0}} sha256:web-image-id")
    printf 'ghcr.io/saksk-it/ti@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa\n'
    ;;
  *"compose "*" ps -q "*) printf '%s-container\n' "${!#}" ;;
  "inspect --format={{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}} "*)
    printf 'healthy\n' ;;
  *" exec -T postgres postgres --version") printf 'postgres (PostgreSQL) 16.4\n' ;;
  *" exec -T redis redis-server --version") printf 'Redis server v=7.2.5 sha=00000000:0 malloc=libc bits=64 build=test\n' ;;
  *" exec -T postgres psql -At "*) printf 'f3c4d5e6a7b8\n' ;;
  *" exec -T postgres psql -X -qAt "*) cat >/dev/null; printf 'users\t42\n' ;;
  *" exec -T postgres pg_dump "*) printf 'FAKE-CUSTOM-PG-DUMP\n' ;;
  *" exec -T postgres pg_restore --list") cat >/dev/null; printf 'TABLE public users\n' ;;
  *" exec -T redis redis-cli --raw DBSIZE") printf '3\n' ;;
  *" exec -T redis redis-cli --raw SAVE") printf '%s\n' "${MIGRATION_FAKE_REDIS_SAVE_OUTPUT:-OK}" ;;
  *"compose "*" stop "*) exit 0 ;;
  *"compose "*" start "*) exit 0 ;;
  *) printf 'unexpected docker invocation: %s\n' "$*" >&2; exit 96 ;;
esac
''',
    )

    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "MIGRATION_DOCKER_BIN": str(fake_bin / "docker"),
            "MIGRATION_SUDO_BIN": str(fake_bin / "sudo"),
            "MIGRATION_GIT_BIN": str(fake_bin / "git"),
            "MIGRATION_MACHINE_ID_FILE": str(machine_id),
            "MIGRATION_FAKE_LOG": str(log),
        }
    )
    return ExportEnvironment(source=source, env=env, log=log)


def log_lines(environment: ExportEnvironment) -> list[str]:
    if not environment.log.exists():
        return []
    return environment.log.read_text(encoding="utf-8").splitlines()


def assert_in_order(lines: list[str], expected: list[str]) -> None:
    position = -1
    for fragment in expected:
        position = next(
            index for index in range(position + 1, len(lines)) if fragment in lines[index]
        )


def output_values(result: subprocess.CompletedProcess[str]) -> dict[str, str]:
    return dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)


def test_exporter_uses_main_guard_and_rejects_unsafe_required_arguments(
    export_environment: ExportEnvironment,
) -> None:
    sourced = subprocess.run(
        ["bash", "-c", 'source "$1"', "bash", str(EXPORTER)],
        cwd=ROOT,
        env=export_environment.env,
        text=True,
        capture_output=True,
        check=False,
    )
    relative = subprocess.run(
        [
            "bash",
            str(EXPORTER),
            "preflight",
            "--source-dir",
            "relative/path",
            "--migration-id",
            "../escape",
        ],
        cwd=ROOT,
        env=export_environment.env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert sourced.returncode == 0
    assert relative.returncode != 0
    assert not export_environment.log.exists()


def test_source_export_preflight_is_read_only_and_reports_safe_facts(
    export_environment: ExportEnvironment,
) -> None:
    result = export_environment.run("preflight")

    assert result.returncode == 0, result.stderr
    values = output_values(result)
    assert values["SOURCE_MACHINE_ID"] == "source-machine-id"
    assert values["SOURCE_GIT_COMMIT"].startswith("01234567")
    assert values["RUNNING_SERVICES"] == "nginx,web,worker,postgres,redis,backup"
    assert values["POSTGRES_MAJOR"] == "16"
    assert values["REDIS_MAJOR"] == "7"
    assert values["WEB_IMAGE_DIGEST"].endswith("sha256:" + "a" * 64)
    assert int(values["DATA_SIZE_KB"]) > 0
    assert int(values["AVAILABLE_KB"]) > int(values["DATA_SIZE_KB"])
    assert values["COMPOSE_SHA256"] == hashlib.sha256(
        (export_environment.source / "compose.prod.yml").read_bytes()
    ).hexdigest()
    assert values["ALEMBIC_VERSION"] == "f3c4d5e6a7b8"
    assert values["UPLOADS_FILE_COUNT"] == "1"
    assert values["INSTANCE_FILE_COUNT"] == "1"
    commands = log_lines(export_environment)
    assert any(" config" in command for command in commands)
    assert not any(" stop " in command for command in commands)
    assert not export_environment.workspace.exists()
    assert not export_environment.lock.exists()


def test_source_export_prepare_has_strict_order_and_verified_bundle_layout(
    export_environment: ExportEnvironment,
) -> None:
    result = export_environment.run("prepare")

    assert result.returncode == 0, result.stderr
    values = output_values(result)
    bundle = Path(values["BUNDLE_PATH"])
    outer_checksum = Path(values["CHECKSUM_PATH"])
    assert bundle.is_file() and outer_checksum.is_file()
    assert stat.S_IMODE(bundle.stat().st_mode) == 0o600
    assert stat.S_IMODE(outer_checksum.stat().st_mode) == 0o600
    assert stat.S_IMODE(export_environment.workspace.stat().st_mode) == 0o700
    assert stat.S_IMODE(export_environment.state.stat().st_mode) == 0o600
    assert "STATUS=FROZEN" in export_environment.state.read_text(encoding="utf-8")
    assert (export_environment.lock / "owner").read_text(encoding="utf-8").strip() == export_environment.migration_id

    commands = log_lines(export_environment)
    assert_in_order(
        commands,
        [
            " stop backup",
            " stop nginx",
            " stop web worker",
            "pg_dump -Fc -Z6 --no-owner --no-acl",
            "pg_restore --list",
            "redis-cli --raw DBSIZE",
            "redis-cli --raw SAVE",
            " stop redis",
        ],
    )

    bundle_validation = subprocess.run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ARCHIVE_VALIDATOR),
            "--archive",
            str(bundle),
            "--profile",
            "bundle",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert bundle_validation.returncode == 0, bundle_validation.stderr
    with tarfile.open(bundle, mode="r:gz") as archive:
        assert archive.getnames() == [
            "database.dump",
            "database-summary.txt",
            "redis.tar.gz",
            "uploads.tar.gz",
            "instance.tar.gz",
            "source.env.production",
            "manifest.txt",
            "checksums.sha256",
        ]
    checksums = (export_environment.workspace / "checksums.sha256").read_text(
        encoding="utf-8"
    ).splitlines()
    assert len(checksums) == 7
    manifest = (export_environment.workspace / "manifest.txt").read_text(
        encoding="utf-8"
    )
    assert "UPLOADS_FILE_COUNT=1\n" in manifest
    assert "UPLOADS_TOTAL_BYTES=6\n" in manifest
    assert "INSTANCE_FILE_COUNT=1\n" in manifest
    assert "INSTANCE_TOTAL_BYTES=8\n" in manifest
    assert "UPLOADS_TREE_SHA256=" in manifest
    assert "INSTANCE_TREE_SHA256=" in manifest
    for line in checksums:
        digest, filename = line.split("  ", 1)
        assert digest == hashlib.sha256(
            (export_environment.workspace / filename).read_bytes()
        ).hexdigest()
    for filename, prefix in (
        ("redis.tar.gz", "redis"),
        ("uploads.tar.gz", "uploads"),
        ("instance.tar.gz", "instance"),
    ):
        inner_validation = subprocess.run(
            [
                str(ROOT / ".venv/bin/python"),
                str(ARCHIVE_VALIDATOR),
                "--archive",
                str(export_environment.workspace / filename),
                "--profile",
                prefix,
            ],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        assert inner_validation.returncode == 0, inner_validation.stderr
        with tarfile.open(export_environment.workspace / filename, mode="r:gz") as archive:
            assert all(name == prefix or name.startswith(f"{prefix}/") for name in archive.getnames())
    expected_outer = hashlib.sha256(bundle.read_bytes()).hexdigest()
    assert outer_checksum.read_text(encoding="utf-8").split()[0] == expected_outer


def test_source_export_prepare_failure_auto_resumes_original_services(
    export_environment: ExportEnvironment,
) -> None:
    result = export_environment.run(
        "prepare",
        MIGRATION_FAKE_RUNNING_SERVICES="nginx web postgres redis",
        MIGRATION_FAKE_FAIL_MATCH="pg_restore --list",
    )

    assert result.returncode != 0
    commands = log_lines(export_environment)
    assert_in_order(
        commands,
        [
            " stop backup",
            " stop nginx",
            " stop web worker",
            "pg_restore --list",
            " start redis",
            " start web",
            " start nginx",
        ],
    )
    assert not any(" start worker" in command for command in commands)
    assert not any(" start backup" in command for command in commands)
    assert not export_environment.lock.exists()
    assert "STATUS=RESUMED" in export_environment.state.read_text(encoding="utf-8")
    assert not (export_environment.workspace / f"migration-{export_environment.migration_id}.tar.gz").exists()


def test_source_export_rejects_unconfirmed_redis_save_and_resumes(
    export_environment: ExportEnvironment,
) -> None:
    result = export_environment.run(
        "prepare",
        MIGRATION_FAKE_RUNNING_SERVICES="nginx web postgres redis",
        MIGRATION_FAKE_REDIS_SAVE_OUTPUT="ERR persistence disabled",
    )

    assert result.returncode != 0
    assert "Redis SAVE" in result.stderr
    assert not export_environment.lock.exists()
    assert "STATUS=RESUMED" in export_environment.state.read_text(encoding="utf-8")


def test_source_export_rejects_foreign_lock_and_unfinished_workspace(
    export_environment: ExportEnvironment,
) -> None:
    export_environment.lock.mkdir(mode=0o700)
    (export_environment.lock / "owner").write_text("other-migration\n", encoding="utf-8")
    locked = export_environment.run("prepare")
    assert locked.returncode != 0

    for child in export_environment.lock.iterdir():
        child.unlink()
    export_environment.lock.rmdir()
    export_environment.workspace.mkdir(mode=0o700)
    export_environment.state.write_text("STATUS=PREPARING\n", encoding="utf-8")
    unfinished = export_environment.run("prepare")
    assert unfinished.returncode != 0
    assert "未完成" in unfinished.stderr


def test_source_export_resume_is_exact_and_idempotent(
    export_environment: ExportEnvironment,
) -> None:
    prepared = export_environment.run(
        "prepare", MIGRATION_FAKE_RUNNING_SERVICES="web postgres redis backup"
    )
    assert prepared.returncode == 0, prepared.stderr
    before_resume = len(log_lines(export_environment))

    resumed = export_environment.run("resume")
    first_lines = log_lines(export_environment)[before_resume:]
    assert resumed.returncode == 0, resumed.stderr
    assert [line.rsplit(" start ", 1)[1] for line in first_lines if " start " in line] == [
        "redis",
        "web",
        "backup",
    ]
    assert "STATUS=RESUMED" in export_environment.state.read_text(encoding="utf-8")
    assert not export_environment.lock.exists()

    command_count = len(log_lines(export_environment))
    resumed_again = export_environment.run("resume")
    assert resumed_again.returncode == 0
    assert len(log_lines(export_environment)) == command_count


def test_source_export_finalize_only_cleans_frozen_artifacts_without_starting(
    export_environment: ExportEnvironment,
) -> None:
    prepared = export_environment.run("prepare")
    assert prepared.returncode == 0, prepared.stderr
    command_count = len(log_lines(export_environment))

    finalized = export_environment.run("finalize")
    finalized_again = export_environment.run("finalize")

    assert finalized.returncode == 0, finalized.stderr
    assert finalized_again.returncode == 0, finalized_again.stderr
    assert not export_environment.workspace.exists()
    assert not export_environment.lock.exists()
    finalized_marker = (
        export_environment.source
        / "backups/migrations"
        / f".finalized-{export_environment.migration_id}"
    )
    assert "STATUS=FINALIZED" in finalized_marker.read_text(encoding="utf-8")
    assert len(log_lines(export_environment)) == command_count
    for path in (
        "var/postgres/PG_VERSION",
        "var/redis/dump.rdb",
        "var/uploads/nested/upload.txt",
        "var/instance/app.db",
    ):
        assert (export_environment.source / path).exists()


def test_source_export_never_logs_env_secrets(export_environment: ExportEnvironment) -> None:
    preflight = export_environment.run("preflight")
    prepared = export_environment.run("prepare")
    combined = "\n".join(
        [preflight.stdout, preflight.stderr, prepared.stdout, prepared.stderr]
        + log_lines(export_environment)
    )

    assert preflight.returncode == 0
    assert prepared.returncode == 0
    for secret in (
        "secret-value-must-not-leak",
        "pg-password-must-not-leak",
        "token-value-must-not-leak",
    ):
        assert secret not in combined
