"""生产数据迁移 Shell 共享原语测试。"""

from __future__ import annotations

import hashlib
import os
import stat
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
COMMON = ROOT / "scripts/lib/production_migration_common.sh"


def run_common(
    function: str,
    *args: str,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    command = 'source "$1"; shift; function="$1"; shift; "$function" "$@"'
    process_env = os.environ.copy()
    if env:
        process_env.update(env)
    return subprocess.run(
        ["bash", "-c", command, "bash", str(COMMON), function, *args],
        cwd=ROOT,
        env=process_env,
        text=True,
        capture_output=True,
        check=False,
    )


@pytest.mark.parametrize(
    ("function", "value"),
    [
        ("migration_validate_ssh_target", "ubuntu@10.0.0.2"),
        ("migration_validate_ssh_target", "deploy@ti-prod.example.com"),
        ("migration_validate_port", "22"),
        ("migration_validate_port", "65535"),
        ("migration_validate_absolute_dir", "/opt/ti"),
        ("migration_validate_absolute_dir", "/srv/ti data"),
        ("migration_validate_id", "20260711T120000Z-a1b2c3"),
    ],
)
def test_common_library_accepts_safe_inputs(function: str, value: str) -> None:
    assert run_common(function, value).returncode == 0


@pytest.mark.parametrize(
    ("function", "value"),
    [
        ("migration_validate_ssh_target", "root@host;id"),
        ("migration_validate_ssh_target", "host.example.com"),
        ("migration_validate_ssh_target", "root@-host"),
        ("migration_validate_port", "0"),
        ("migration_validate_port", "65536"),
        ("migration_validate_port", "22;id"),
        ("migration_validate_port", "PORT_ALIAS"),
        ("migration_validate_port", "18446744073709551617"),
        ("migration_validate_absolute_dir", "opt/ti"),
        ("migration_validate_absolute_dir", "/opt/../root"),
        ("migration_validate_absolute_dir", "/opt/./ti"),
        ("migration_validate_absolute_dir", "/opt/ti\tunsafe"),
        ("migration_validate_absolute_dir", "/opt/ti\x1bunsafe"),
        ("migration_validate_id", "../escape"),
        ("migration_validate_id", "id;touch-pwned"),
    ],
)
def test_common_library_rejects_unsafe_inputs(function: str, value: str) -> None:
    assert run_common(function, value).returncode != 0


def test_common_library_sets_private_umask() -> None:
    result = subprocess.run(
        ["bash", "-c", 'source "$1"; umask', "bash", str(COMMON)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert result.stdout.strip().endswith("077")


def test_common_library_port_validation_never_evaluates_arithmetic_input(
    tmp_path: Path,
) -> None:
    marker = tmp_path / "must-not-exist"
    payload = f"x[$(touch {marker})]"

    result = run_common("migration_validate_port", payload)

    assert result.returncode != 0
    assert not marker.exists()


def test_common_library_reads_env_as_data_without_execution(tmp_path: Path) -> None:
    marker = tmp_path / "executed"
    env_file = tmp_path / ".env.production"
    env_file.write_text(
        f'export SECRET_KEY="literal value"\nEVIL=$(touch {marker})\n',
        encoding="utf-8",
    )

    secret = run_common("migration_read_env_value", str(env_file), "SECRET_KEY")
    evil = run_common("migration_read_env_value", str(env_file), "EVIL")

    assert secret.returncode == 0
    assert secret.stdout == "literal value\n"
    assert evil.stdout == f"$(touch {marker})\n"
    assert not marker.exists()


def test_common_library_rejects_invalid_env_key_before_reading(tmp_path: Path) -> None:
    env_file = tmp_path / ".env.production"
    env_file.write_text("BAD-KEY=must-not-return\n", encoding="utf-8")

    result = run_common("migration_read_env_value", str(env_file), "BAD-KEY")

    assert result.returncode != 0
    assert result.stdout == ""
    assert "env 键名无效" in result.stderr


def test_common_library_missing_env_file_returns_failure(tmp_path: Path) -> None:
    result = run_common(
        "migration_read_env_value",
        str(tmp_path / "missing.env"),
        "SECRET_KEY",
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "env 文件不存在" in result.stderr

    special_file = run_common("migration_read_env_value", "/dev/null", "SECRET_KEY")
    assert special_file.returncode != 0
    assert special_file.stdout == ""


def test_common_library_emits_portable_sha256(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"migration-payload\n")

    result = run_common("migration_sha256", str(payload))

    assert result.returncode == 0
    assert result.stdout.strip() == hashlib.sha256(payload.read_bytes()).hexdigest()


def test_common_library_sha256_falls_back_to_shasum(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"fallback\n")
    fake_shasum = tmp_path / "shasum"
    _write_executable(
        fake_shasum,
        '[[ "$1" == "-a" && "$2" == "256" ]] || exit 91\n'
        'printf "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa  %s\\n" "$3"\n',
    )

    result = run_common(
        "migration_sha256",
        str(payload),
        env={
            "MIGRATION_SHA256SUM_BIN": str(tmp_path / "missing-sha256sum"),
            "MIGRATION_SHASUM_BIN": str(fake_shasum),
        },
    )

    assert result.returncode == 0
    assert result.stdout == ("a" * 64) + "\n"


def test_common_library_sha256_fails_when_no_tool_exists(tmp_path: Path) -> None:
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"missing\n")
    result = run_common(
        "migration_sha256",
        str(payload),
        env={
            "MIGRATION_SHA256SUM_BIN": str(tmp_path / "missing-a"),
            "MIGRATION_SHASUM_BIN": str(tmp_path / "missing-b"),
        },
    )

    assert result.returncode != 0
    assert "缺少 sha256sum 或 shasum" in result.stderr


def test_common_library_sha256_propagates_tool_failure(tmp_path: Path) -> None:
    missing_payload = tmp_path / "missing.bin"
    failing_sha = tmp_path / "sha256sum"
    _write_executable(failing_sha, 'echo "hash failed" >&2; exit 7\n')

    result = run_common(
        "migration_sha256",
        str(missing_payload),
        env={"MIGRATION_SHA256SUM_BIN": str(failing_sha)},
    )

    assert result.returncode != 0
    assert result.stdout == ""


def _write_executable(path: Path, body: str) -> None:
    path.write_text(f"#!/usr/bin/env bash\n{body}", encoding="utf-8")
    path.chmod(0o755)


def test_common_library_fail_and_require_command_return_nonzero(tmp_path: Path) -> None:
    failed = run_common("migration_fail", "expected failure")
    missing = run_common(
        "migration_require_command",
        str(tmp_path / "missing-command"),
    )

    assert failed.returncode != 0
    assert "expected failure" in failed.stderr
    assert missing.returncode != 0
    assert "缺少必需命令" in missing.stderr


def test_common_library_root_fails_when_noninteractive_sudo_is_unavailable(
    tmp_path: Path,
) -> None:
    fake_id = tmp_path / "id"
    fake_sudo = tmp_path / "sudo"
    _write_executable(fake_id, 'if [[ "$1" == "-u" ]]; then echo 501; fi\n')
    _write_executable(fake_sudo, 'echo "sudo denied" >&2; exit 1\n')
    env = {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "MIGRATION_SUDO_BIN": str(fake_sudo),
    }

    result = run_common("migration_root", "printf", "should-not-run", env=env)

    assert result.returncode != 0
    assert "should-not-run" not in result.stdout
    assert "non-interactive" in result.stderr.lower()


def test_common_library_root_runs_directly_for_root(tmp_path: Path) -> None:
    fake_id = tmp_path / "id"
    output = tmp_path / "output"
    _write_executable(fake_id, '[[ "$1" == "-u" ]] && echo 0\n')
    result = run_common(
        "migration_root",
        "bash",
        "-c",
        'printf "%s" "$1" > "$2"',
        "bash",
        "direct-value",
        str(output),
        env={"PATH": f"{tmp_path}:{os.environ['PATH']}"},
    )

    assert result.returncode == 0
    assert output.read_text(encoding="utf-8") == "direct-value"


def test_common_library_root_uses_noninteractive_sudo_and_preserves_args(
    tmp_path: Path,
) -> None:
    fake_id = tmp_path / "id"
    fake_sudo = tmp_path / "sudo"
    calls = tmp_path / "calls"
    _write_executable(fake_id, '[[ "$1" == "-u" ]] && echo 501\n')
    _write_executable(
        fake_sudo,
        'printf "<%s>\\n" "$@" >> "$MIGRATION_CALLS"\n'
        'if [[ "$1" == "-n" && "$2" == "true" ]]; then exit 0; fi\n'
        '[[ "$1" == "-n" ]] || exit 92\n'
        'shift\nexec "$@"\n',
    )
    result = run_common(
        "migration_root",
        "printf",
        "%s|%s",
        "value with spaces",
        "literal;semicolon",
        env={
            "PATH": f"{tmp_path}:{os.environ['PATH']}",
            "MIGRATION_SUDO_BIN": str(fake_sudo),
            "MIGRATION_CALLS": str(calls),
        },
    )

    assert result.returncode == 0
    assert result.stdout == "value with spaces|literal;semicolon"
    assert "<value with spaces>" in calls.read_text(encoding="utf-8")


def test_common_library_directory_lock_is_exclusive_and_releasable(
    tmp_path: Path,
) -> None:
    lock_dir = tmp_path / "migration.lock"
    command = (
        'source "$1"; migration_lock_acquire "$2"; '
        'migration_lock_acquire "$2" >/dev/null 2>&1 && exit 91; '
        'migration_lock_release "$2"; migration_lock_acquire "$2"'
    )

    result = subprocess.run(
        ["bash", "-c", command, "bash", str(COMMON), str(lock_dir)],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert lock_dir.is_dir()
    assert stat.S_IMODE(lock_dir.stat().st_mode) == 0o700


def test_common_library_lock_release_requires_matching_owner(tmp_path: Path) -> None:
    lock_dir = tmp_path / "migration.lock"

    acquired = run_common("migration_lock_acquire", str(lock_dir), "owner-one")
    rejected = run_common("migration_lock_release", str(lock_dir), "owner-two")
    released = run_common("migration_lock_release", str(lock_dir), "owner-one")

    assert acquired.returncode == 0
    assert rejected.returncode != 0
    assert released.returncode == 0
    assert not lock_dir.exists()


def test_common_library_state_is_atomic_private_and_read_without_source(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.env"
    marker = tmp_path / "executed"
    write = run_common(
        "migration_state_write",
        str(state_file),
        "PHASE",
        "FROZEN",
        "SERVICES",
        "nginx web",
        "LITERAL",
        f"$(touch {marker})",
    )

    assert write.returncode == 0
    assert stat.S_IMODE(state_file.stat().st_mode) == 0o600
    assert not list(tmp_path.glob(".state.env.tmp.*"))
    assert run_common("migration_state_read", str(state_file), "PHASE").stdout == "FROZEN\n"
    assert run_common("migration_state_read", str(state_file), "SERVICES").stdout == "nginx web\n"
    literal = run_common("migration_state_read", str(state_file), "LITERAL")
    assert literal.stdout == f"$(touch {marker})\n"
    assert not marker.exists()


def test_common_library_state_preserves_existing_parent_directory_mode(
    tmp_path: Path,
) -> None:
    shared_dir = tmp_path / "shared"
    shared_dir.mkdir(mode=0o755)
    shared_dir.chmod(0o755)
    state_file = shared_dir / "state.env"

    result = run_common("migration_state_write", str(state_file), "PHASE", "FROZEN")

    assert result.returncode == 0
    assert stat.S_IMODE(shared_dir.stat().st_mode) == 0o755
    assert stat.S_IMODE(state_file.stat().st_mode) == 0o600


def test_common_library_state_rejects_backslash_escape_without_modifying_file(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.env"
    state_file.write_bytes(b"PHASE=FROZEN\n")

    result = run_common(
        "migration_state_write",
        str(state_file),
        "SERVICES",
        r"web\nEVIL=1",
    )

    assert result.returncode != 0
    assert state_file.read_bytes() == b"PHASE=FROZEN\n"
    assert not list(tmp_path.glob(".state.env.tmp.*"))


@pytest.mark.parametrize("arguments", [(), ("ONLY_KEY",)])
def test_common_library_state_rejects_missing_or_odd_key_value_pairs(
    tmp_path: Path,
    arguments: tuple[str, ...],
) -> None:
    state_file = tmp_path / "state.env"

    result = run_common("migration_state_write", str(state_file), *arguments)

    assert result.returncode != 0
    assert not state_file.exists()
    assert not list(tmp_path.glob(".state.env.tmp.*"))


def test_common_library_state_awk_failure_preserves_original_and_cleans_temp(
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "state.env"
    state_file.write_bytes(b"PHASE=FROZEN\n")
    fake_awk = tmp_path / "awk"
    _write_executable(fake_awk, 'echo "awk failed" >&2; exit 77\n')

    result = run_common(
        "migration_state_write",
        str(state_file),
        "PHASE",
        "RESUMED",
        env={"PATH": f"{tmp_path}:{os.environ['PATH']}"},
    )

    assert result.returncode != 0
    assert state_file.read_bytes() == b"PHASE=FROZEN\n"
    assert not list(tmp_path.glob(".state.env.tmp.*"))


def test_common_library_captures_running_services_with_array_execution(
    tmp_path: Path,
) -> None:
    fake_docker = tmp_path / "docker"
    calls = tmp_path / "calls"
    _write_executable(
        fake_docker,
        'printf "%s\\n" "$@" > "$MIGRATION_CALLS"\n'
        'printf "nginx\\nweb\\nworker\\n"\n',
    )
    result = run_common(
        "migration_capture_running_services",
        env={
            "MIGRATION_DOCKER_BIN": str(fake_docker),
            "MIGRATION_CALLS": str(calls),
        },
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == ["nginx", "web", "worker"]
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "compose",
        "--env-file",
        ".env.production",
        "-f",
        "compose.prod.yml",
        "ps",
        "--services",
        "--filter",
        "status=running",
    ]


def test_common_library_compose_wrappers_preserve_argument_boundaries(
    tmp_path: Path,
) -> None:
    fake_docker = tmp_path / "docker"
    fake_id = tmp_path / "id"
    calls = tmp_path / "calls"
    _write_executable(fake_id, '[[ "$1" == "-u" ]] && echo 0\n')
    _write_executable(fake_docker, 'printf "<%s>\\n" "$@" >> "$MIGRATION_CALLS"\n')
    env = {
        "PATH": f"{tmp_path}:{os.environ['PATH']}",
        "MIGRATION_DOCKER_BIN": str(fake_docker),
        "MIGRATION_CALLS": str(calls),
        "MIGRATION_ENV_FILE": "/opt/ti/env with spaces",
        "MIGRATION_COMPOSE_FILE": "/opt/ti/compose.prod.yml",
    }

    direct = run_common("migration_compose", "ps", "--format", "json value", env=env)
    rooted = run_common("migration_root_compose", "stop", "web", env=env)

    assert direct.returncode == 0
    assert rooted.returncode == 0
    logged = calls.read_text(encoding="utf-8")
    assert "</opt/ti/env with spaces>" in logged
    assert "<json value>" in logged


def test_common_library_logs_do_not_expose_known_secret_values() -> None:
    result = run_common(
        "migration_log",
        "INFO",
        (
            "operation secret-value db-password third-party-token "
            "api-key-value private-key-value"
        ),
        env={
            "SECRET_KEY": "secret-value",
            "POSTGRES_PASSWORD": "db-password",
            "THIRD_PARTY_TOKEN": "third-party-token",
            "OPENAI_API_KEY": "api-key-value",
            "PRIVATE_KEY": "private-key-value",
        },
    )

    assert result.returncode == 0
    assert "secret-value" not in result.stderr
    assert "db-password" not in result.stderr
    assert "third-party-token" not in result.stderr
    assert "api-key-value" not in result.stderr
    assert "private-key-value" not in result.stderr
    assert result.stderr.count("[REDACTED]") == 5


def test_common_library_redacts_longest_overlapping_secret_first() -> None:
    result = run_common(
        "migration_log",
        "INFO",
        "overlap foobar bar",
        env={"API_KEY": "bar", "PRIVATE_KEY": "foobar"},
    )

    assert result.returncode == 0
    assert "foo[REDACTED]" not in result.stderr
    assert "foobar" not in result.stderr
    assert " bar" not in result.stderr
    assert result.stderr.count("[REDACTED]") == 2
