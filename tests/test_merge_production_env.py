from __future__ import annotations

from pathlib import Path
import stat
import subprocess
from types import ModuleType

import pytest

from tests.production_migration_test_support import (
    load_python_helper,
    run_python_helper,
)


TARGET_LOCAL_KEYS = (
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
    "POSTGRES_DB",
    "TI_IMAGE",
    "TI_IMAGE_PULL_POLICY",
    "HTTP_BIND",
    "HTTP_PORT",
    "ENABLE_HTTPS",
    "DOMAIN",
    "EXTRA_DOMAINS",
    "CERTBOT_EMAIL",
    "SESSION_COOKIE_SECURE",
)
ORIGINAL_ENV_OUTPUT = b"ORIGINAL_OUTPUT=must-remain\n"
DOTENV_EMPTY_VALUES = (
    "",
    " ",
    "\t",
    "''",
    '""',
    "'' # trailing comment",
    '"" # trailing comment',
    "# comment",
    "  # comment",
)


def install_atomic_write_recorders(
    helper: ModuleType,
    output: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, object]]:
    events: list[tuple[str, object]] = []
    directory_file_descriptors: list[int] = []
    real_mkstemp = helper.tempfile.mkstemp
    real_fsync = helper.os.fsync
    real_open = helper.os.open
    real_replace = helper.os.replace

    def recording_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        events.append(("mkstemp", Path(kwargs["dir"])))
        return real_mkstemp(*args, **kwargs)

    def recording_fsync(file_descriptor: int) -> None:
        event_name = "directory-fsync" if directory_file_descriptors else "file-fsync"
        events.append((event_name, file_descriptor))
        real_fsync(file_descriptor)

    def recording_open(path: Path, flags: int, *args: object) -> int:
        file_descriptor = real_open(path, flags, *args)
        if Path(path) == output.parent:
            directory_file_descriptors.append(file_descriptor)
            events.append(("directory-open", Path(path)))
        return file_descriptor

    def recording_replace(source: Path, destination: Path) -> None:
        events.append(("replace", (Path(source), Path(destination))))
        real_replace(source, destination)

    monkeypatch.setattr(helper.tempfile, "mkstemp", recording_mkstemp)
    monkeypatch.setattr(helper.os, "fsync", recording_fsync)
    monkeypatch.setattr(helper.os, "open", recording_open)
    monkeypatch.setattr(helper.os, "replace", recording_replace)
    return events


def write_env(path: Path, records: dict[str, str]) -> None:
    path.write_text(
        "".join(f"{key}={value}\n" for key, value in records.items()),
        encoding="utf-8",
    )


def run_env_merge(source: Path, target: Path, output: Path) -> subprocess.CompletedProcess[str]:
    return run_python_helper(
        "scripts/lib/merge_production_env.py",
        "--source",
        str(source),
        "--target",
        str(target),
        "--output",
        str(output),
    )


def double_quote_env_value(value: str) -> str:
    escaped_value = value
    for original, replacement in (
        ("\\", "\\\\"),
        ('"', '\\"'),
        ("$", "\\$"),
        ("`", "\\`"),
    ):
        escaped_value = escaped_value.replace(original, replacement)
    return f'"{escaped_value}"'


def required_target_env(**overrides: str) -> dict[str, str]:
    values = {
        "POSTGRES_USER": "target-user",
        "POSTGRES_PASSWORD": "target-password",
        "POSTGRES_DB": "target-database",
    }
    return {**values, **overrides}


def test_env_merge_uses_source_secrets_and_all_target_local_values(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    source_records = {
        "SECRET_KEY": "source-secret",
        "DASHSCOPE_API_KEY": "source-ai",
        **{key: f"source-{index}" for index, key in enumerate(TARGET_LOCAL_KEYS)},
    }
    target_records = {
        "SECRET_KEY": "target-secret",
        "DASHSCOPE_API_KEY": "target-ai",
        **{key: f"target-{index}" for index, key in enumerate(TARGET_LOCAL_KEYS)},
    }
    write_env(source, source_records)
    write_env(target, target_records)

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    merged = output.read_text(encoding="utf-8")
    assert f"SECRET_KEY={double_quote_env_value('source-secret')}\n" in merged
    assert f"DASHSCOPE_API_KEY={double_quote_env_value('source-ai')}\n" in merged
    assert "target-secret" not in merged
    assert "target-ai" not in merged
    for index, key in enumerate(TARGET_LOCAL_KEYS):
        assert f"{key}={double_quote_env_value(f'target-{index}')}\n" in merged
        assert f"{key}={double_quote_env_value(f'source-{index}')}\n" not in merged


def test_env_merge_preserves_target_only_forward_compatible_keys(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret"})
    write_env(
        target,
        {**required_target_env(), "NEW_REQUIRED_DEPLOYMENT_SECRET": "target-new"},
    )

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    assert (
        f"NEW_REQUIRED_DEPLOYMENT_SECRET={double_quote_env_value('target-new')}\n"
        in output.read_text(encoding="utf-8")
    )


@pytest.mark.parametrize("duplicate_in", ["source", "target"])
def test_env_merge_rejects_duplicate_keys(tmp_path: Path, duplicate_in: str) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret", "BUSINESS_KEY": "source-value"})
    write_env(target, required_target_env())
    duplicate_path = source if duplicate_in == "source" else target
    duplicate_key = "SECRET_KEY" if duplicate_in == "source" else "POSTGRES_USER"
    with duplicate_path.open("a", encoding="utf-8") as env_file:
        env_file.write(f"{duplicate_key}=duplicate\n")
    output.write_bytes(ORIGINAL_ENV_OUTPUT)

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert "重复键" in result.stderr
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT


@pytest.mark.parametrize("malformed_in", ["source", "target"])
def test_env_merge_rejects_malformed_non_comment_lines(
    tmp_path: Path,
    malformed_in: str,
) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret"})
    write_env(target, required_target_env())
    malformed_path = source if malformed_in == "source" else target
    with malformed_path.open("a", encoding="utf-8") as env_file:
        env_file.write("not an env record\n")
    output.write_bytes(ORIGINAL_ENV_OUTPUT)

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert "格式错误" in result.stderr
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT


def test_env_merge_requires_source_secret_key(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"BUSINESS_KEY": "source-value"})
    write_env(target, required_target_env(SECRET_KEY="target-secret"))
    output.write_bytes(ORIGINAL_ENV_OUTPUT)

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert "源 env 缺少必需键: SECRET_KEY" in result.stderr
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT


@pytest.mark.parametrize("missing_key", ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"])
def test_env_merge_requires_target_postgres_keys(tmp_path: Path, missing_key: str) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret", missing_key: "source-value"})
    target_records = required_target_env()
    target_records.pop(missing_key)
    write_env(target, target_records)
    output.write_bytes(ORIGINAL_ENV_OUTPUT)

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert f"目标 env 缺少必需键: {missing_key}" in result.stderr
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT


@pytest.mark.parametrize("empty_value", DOTENV_EMPTY_VALUES)
@pytest.mark.parametrize(
    ("env_location", "required_key"),
    [
        ("source", "SECRET_KEY"),
        ("target", "POSTGRES_USER"),
        ("target", "POSTGRES_PASSWORD"),
        ("target", "POSTGRES_DB"),
    ],
)
def test_env_merge_rejects_dotenv_empty_required_value(
    tmp_path: Path,
    empty_value: str,
    env_location: str,
    required_key: str,
) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    source_value = empty_value if env_location == "source" else "source-secret"
    target_overrides = {required_key: empty_value} if env_location == "target" else {}
    write_env(source, {"SECRET_KEY": source_value})
    write_env(target, required_target_env(**target_overrides))

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    env_label = "源 env" if env_location == "source" else "目标 env"
    assert f"{env_label} 缺少必需键: {required_key}" in result.stderr
    assert not output.exists()


@pytest.mark.parametrize(
    ("limit_name", "limit", "contents", "error_message"),
    [
        ("MAX_ENV_FILE_SIZE_BYTES", 8, "SECRET_KEY=too-large\n", "env 文件过大"),
        ("MAX_ENV_LINES", 1, "FIRST=value\nSECOND=value\n", "env 文件行数过多"),
        ("MAX_ENV_LINE_BYTES", 12, "KEY=题题题题\n", "env 文件行过长"),
    ],
)
def test_env_parser_enforces_resource_limits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    limit_name: str,
    limit: int,
    contents: str,
    error_message: str,
) -> None:
    helper = load_python_helper("scripts/lib/merge_production_env.py")
    env_path = tmp_path / "limited.env"
    env_path.write_text(contents, encoding="utf-8")
    monkeypatch.setattr(helper, limit_name, limit)

    with pytest.raises(helper.EnvMergeError, match=error_message):
        helper.parse_env_file(env_path)


def test_env_merge_failure_does_not_modify_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret"})
    write_env(target, {"POSTGRES_USER": "target-user"})
    output.write_bytes(ORIGINAL_ENV_OUTPUT)

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT


def test_env_merge_treats_shell_syntax_as_literal_data(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    marker = tmp_path / "must-not-exist"
    backtick_marker = tmp_path / "backtick-must-not-exist"
    literal_secret = f"$(touch {marker})"
    literal_reference = "${MISSING}"
    literal_backtick = f"`touch {backtick_marker}`"
    write_env(
        source,
        {
            "SECRET_KEY": literal_secret,
            "BUSINESS_KEY": literal_reference,
            "BACKTICK_KEY": literal_backtick,
        },
    )
    write_env(target, required_target_env())

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    merged = output.read_text(encoding="utf-8")
    assert f"SECRET_KEY={double_quote_env_value(literal_secret)}\n" in merged
    assert f"BUSINESS_KEY={double_quote_env_value(literal_reference)}\n" in merged
    assert f"BACKTICK_KEY={double_quote_env_value(literal_backtick)}\n" in merged

    sourced = subprocess.run(
        [
            "bash",
            "-c",
            'set -u; source "$1"; printf "%s\\0%s\\0%s" '
            '"$SECRET_KEY" "$BUSINESS_KEY" "$BACKTICK_KEY"',
            "bash",
            str(output),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )

    assert sourced.returncode == 0, sourced.stderr
    assert sourced.stdout.split("\0") == [literal_secret, literal_reference, literal_backtick]
    assert not marker.exists()
    assert not backtick_marker.exists()


def test_env_merge_parses_quotes_and_unquoted_trailing_comments(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    source.write_text(
        "SECRET_KEY='source secret' # source comment\n"
        "BUSINESS_KEY=value with spaces # trailing comment\n"
        "HASH_KEY='#literal hash' # trailing comment\n",
        encoding="utf-8",
    )
    write_env(target, required_target_env())

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    merged = output.read_text(encoding="utf-8")
    assert f"SECRET_KEY={double_quote_env_value('source secret')}\n" in merged
    assert f"BUSINESS_KEY={double_quote_env_value('value with spaces')}\n" in merged
    assert f"HASH_KEY={double_quote_env_value('#literal hash')}\n" in merged


@pytest.mark.parametrize(
    "value_template",
    [
        "pa'ss",
        'say "hello"',
        "$(touch {marker})",
        "${MISSING}",
        "`touch {marker}`",
        r"C:\path\file",
        "value with spaces",
        "#literal hash",
    ],
)
def test_env_serialization_round_trips_and_is_safe_to_source(
    tmp_path: Path,
    value_template: str,
) -> None:
    helper = load_python_helper("scripts/lib/merge_production_env.py")
    marker = tmp_path / "round-trip-marker"
    value = value_template.replace("{marker}", str(marker))
    env_path = tmp_path / "round-trip.env"
    serialized = helper.serialize_env({"ROUND_TRIP": value})
    env_path.write_text(serialized, encoding="utf-8")

    assert serialized == f"ROUND_TRIP={double_quote_env_value(value)}\n"
    assert helper.parse_env_file(env_path) == {"ROUND_TRIP": value}

    sourced = subprocess.run(
        ["bash", "-c", 'set -u; source "$1"; printf "%s" "$ROUND_TRIP"', "bash", str(env_path)],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert sourced.returncode == 0, sourced.stderr
    assert sourced.stdout == value
    assert not marker.exists()


@pytest.mark.parametrize("quote", ["'", '\"'])
def test_env_merge_rejects_unclosed_quoted_value(tmp_path: Path, quote: str) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    source.write_text(f"SECRET_KEY={quote}unclosed\n", encoding="utf-8")
    write_env(target, required_target_env())

    result = run_env_merge(source, target, output)

    assert result.returncode != 0
    assert "引号未闭合" in result.stderr
    assert not output.exists()


def test_env_merge_removes_registry_credentials(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    credential_keys = ("GHCR_TOKEN", "GHCR_USERNAME", "DOCKER_AUTH_CONFIG")
    write_env(
        source,
        {
            "SECRET_KEY": "source-secret",
            "BUSINESS_KEY": "source-value",
            **{key: f"source-{key}" for key in credential_keys},
        },
    )
    write_env(
        target,
        {
            **required_target_env(),
            **{key: f"target-{key}" for key in credential_keys},
        },
    )

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    merged = output.read_text(encoding="utf-8")
    assert f"BUSINESS_KEY={double_quote_env_value('source-value')}\n" in merged
    for key in credential_keys:
        assert f"{key}=" not in merged


def test_env_merge_removes_compose_and_docker_control_keys(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(
        source,
        {
            "SECRET_KEY": "source-secret",
            "COMPOSE_PROJECT_NAME": "source-project",
            "COMPOSE_FILE": "attacker.yml",
            "DOCKER_HOST": "tcp://source:2375",
        },
    )
    write_env(
        target,
        {**required_target_env(), "DOCKER_CONTEXT": "production"},
    )

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    merged = output.read_text(encoding="utf-8")
    for key in (
        "COMPOSE_PROJECT_NAME",
        "COMPOSE_FILE",
        "DOCKER_HOST",
        "DOCKER_CONTEXT",
    ):
        assert f"{key}=" not in merged


def test_env_merge_writes_output_with_mode_0600(tmp_path: Path) -> None:
    source = tmp_path / "source.env"
    target = tmp_path / "target.env"
    output = tmp_path / "merged.env"
    write_env(source, {"SECRET_KEY": "source-secret"})
    write_env(target, required_target_env())

    result = run_env_merge(source, target, output)

    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_env_merge_atomic_write_uses_same_directory_fsync_and_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/merge_production_env.py")
    output_parent = tmp_path / "env-directory"
    output_parent.mkdir()
    output = output_parent / ".env.production"
    events = install_atomic_write_recorders(helper, output, monkeypatch)

    helper.atomic_write(output, "SECRET_KEY=source-secret\n")

    assert [event_name for event_name, _ in events] == [
        "mkstemp",
        "file-fsync",
        "replace",
        "directory-open",
        "directory-fsync",
    ]
    assert events[0][1] == output.parent
    replace_source, replace_destination = events[2][1]
    assert replace_source.parent == output.parent
    assert replace_destination == output
    assert output.read_text(encoding="utf-8") == "SECRET_KEY=source-secret\n"


def test_env_merge_atomic_write_replace_failure_preserves_output_and_cleans_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/merge_production_env.py")
    output = tmp_path / ".env.production"
    output.write_bytes(ORIGINAL_ENV_OUTPUT)
    output.chmod(0o640)
    original_mode = stat.S_IMODE(output.stat().st_mode)
    replace_calls: list[tuple[Path, Path]] = []

    def failing_replace(source: Path, destination: Path) -> None:
        replace_calls.append((Path(source), Path(destination)))
        raise OSError("simulated replace failure")

    monkeypatch.setattr(helper.os, "replace", failing_replace)

    with pytest.raises(helper.EnvMergeError, match="无法原子写入"):
        helper.atomic_write(output, "SECRET_KEY=replacement\n")

    assert len(replace_calls) == 1
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT
    assert stat.S_IMODE(output.stat().st_mode) == original_mode
    assert list(tmp_path.glob(f".{output.name}.*.tmp")) == []


def test_env_merge_cleanup_error_does_not_mask_replace_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/merge_production_env.py")
    output = tmp_path / ".env.production"
    output.write_bytes(ORIGINAL_ENV_OUTPUT)
    unlink_calls: list[Path] = []

    def failing_replace(source: Path, destination: Path) -> None:
        raise OSError("simulated replace failure")

    def failing_unlink(path: Path, *args: object, **kwargs: object) -> None:
        unlink_calls.append(path)
        raise OSError("simulated cleanup failure")

    monkeypatch.setattr(helper.os, "replace", failing_replace)
    monkeypatch.setattr(helper.Path, "unlink", failing_unlink)

    with pytest.raises(helper.EnvMergeError, match="simulated replace failure"):
        helper.atomic_write(output, "SECRET_KEY=replacement\n")

    assert len(unlink_calls) == 1
    assert output.read_bytes() == ORIGINAL_ENV_OUTPUT
