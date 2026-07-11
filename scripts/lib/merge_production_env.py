#!/usr/bin/env python3
"""Safely merge production env files without evaluating their contents."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import sys
import tempfile


TARGET_LOCAL_KEYS = frozenset(
    {
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
    }
)
REQUIRED_SOURCE_KEYS = frozenset({"SECRET_KEY"})
REQUIRED_TARGET_KEYS = frozenset(
    {"POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"}
)
EXCLUDED_CREDENTIAL_KEYS = frozenset(
    {"GHCR_TOKEN", "GHCR_USERNAME", "DOCKER_AUTH_CONFIG"}
)
EXCLUDED_CONTROL_PREFIXES = ("COMPOSE_", "DOCKER_")
ENV_KEY_PATTERN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
MAX_ENV_FILE_SIZE_BYTES = 16 * 1024 * 1024
MAX_ENV_LINES = 100_000
MAX_ENV_LINE_BYTES = 1024 * 1024


class EnvMergeError(ValueError):
    """Raised when an env input or output violates the merge contract."""


def parse_quoted_value(
    value: str,
    path: Path,
    line_number: int,
) -> str:
    quote = value[0]
    characters: list[str] = []
    index = 1
    while index < len(value):
        character = value[index]
        if quote == '"' and character == "\\" and index + 1 < len(value):
            escaped_character = value[index + 1]
            if escaped_character in {'"', "\\", "$", "`"}:
                characters.append(escaped_character)
            else:
                characters.extend(("\\", escaped_character))
            index += 2
            continue
        if character == quote:
            trailing_content = value[index + 1 :].strip()
            if trailing_content and not trailing_content.startswith("#"):
                raise EnvMergeError(
                    f"env 文件 {path} 第 {line_number} 行引号值后存在非法内容"
                )
            return "".join(characters)
        characters.append(character)
        index += 1

    raise EnvMergeError(f"env 文件 {path} 第 {line_number} 行引号未闭合")


def parse_env_value(value: str, path: Path, line_number: int) -> str:
    stripped_value = value.strip()
    if not stripped_value:
        return ""
    if stripped_value[0] in {"'", '"'}:
        return parse_quoted_value(stripped_value, path, line_number)

    for index, character in enumerate(stripped_value):
        if character == "#" and (
            index == 0 or stripped_value[index - 1].isspace()
        ):
            return stripped_value[:index].rstrip()
    return stripped_value


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a dotenv-like file as inert KEY=VALUE records."""
    try:
        with path.open("rb") as env_file:
            raw_contents = env_file.read(MAX_ENV_FILE_SIZE_BYTES + 1)
    except OSError as error:
        raise EnvMergeError(f"无法读取 env 文件 {path}: {error}") from error

    if len(raw_contents) > MAX_ENV_FILE_SIZE_BYTES:
        raise EnvMergeError(f"env 文件过大: {path}")
    try:
        lines = raw_contents.decode("utf-8").splitlines()
    except UnicodeError as error:
        raise EnvMergeError(f"env 文件不是有效 UTF-8: {path}") from error
    if len(lines) > MAX_ENV_LINES:
        raise EnvMergeError(f"env 文件行数过多: {path}")

    records: dict[str, str] = {}
    for line_number, line in enumerate(lines, start=1):
        if len(line.encode("utf-8")) > MAX_ENV_LINE_BYTES:
            raise EnvMergeError(f"env 文件行过长: {path} 第 {line_number} 行")
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if "=" not in line:
            raise EnvMergeError(f"env 文件 {path} 第 {line_number} 行格式错误")

        key, value = line.split("=", maxsplit=1)
        if ENV_KEY_PATTERN.fullmatch(key) is None:
            raise EnvMergeError(f"env 文件 {path} 第 {line_number} 行键名无效")
        if key in records:
            raise EnvMergeError(f"env 文件 {path} 包含重复键 {key}")

        records[key] = parse_env_value(value, path, line_number)

    return records


def is_dotenv_empty(value: str) -> bool:
    return not value.strip()


def require_nonempty_keys(
    values: dict[str, str],
    required_keys: frozenset[str],
    source_name: str,
) -> None:
    missing_keys = sorted(
        key
        for key in required_keys
        if key not in values or is_dotenv_empty(values[key])
    )
    if missing_keys:
        raise EnvMergeError(
            f"{source_name} 缺少必需键: {', '.join(missing_keys)}"
        )


def merge_env_values(
    source_values: dict[str, str],
    target_values: dict[str, str],
) -> dict[str, str]:
    """Return a new merged mapping without mutating either input mapping."""
    require_nonempty_keys(source_values, REQUIRED_SOURCE_KEYS, "源 env")
    require_nonempty_keys(target_values, REQUIRED_TARGET_KEYS, "目标 env")

    target_overrides = {
        key: value
        for key, value in target_values.items()
        if key in TARGET_LOCAL_KEYS
    }
    # Keep target-only keys for forward compatibility with a freshly deployed
    # server 2, while source values still win whenever both sides define a
    # business setting. Explicit target-local keys always override the source.
    merged_values = {**target_values, **source_values, **target_overrides}
    return {
        key: value
        for key, value in merged_values.items()
        if key not in EXCLUDED_CREDENTIAL_KEYS
        and not key.startswith(EXCLUDED_CONTROL_PREFIXES)
    }


def serialize_env(values: dict[str, str]) -> str:
    def quote_value(value: str) -> str:
        escaped_value = value
        for original, replacement in (
            ("\\", "\\\\"),
            ('"', '\\"'),
            ("$", "\\$"),
            ("`", "\\`"),
        ):
            escaped_value = escaped_value.replace(original, replacement)
        return f'"{escaped_value}"'

    return "".join(
        f"{key}={quote_value(value)}\n"
        for key, value in values.items()
    )


def atomic_write(path: Path, contents: str) -> None:
    """Write contents durably and atomically with owner-only permissions."""
    parent = path.parent
    temporary_path: Path | None = None
    file_descriptor: int | None = None
    try:
        file_descriptor, raw_temporary_path = tempfile.mkstemp(
            dir=parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
        )
        temporary_path = Path(raw_temporary_path)
        os.fchmod(file_descriptor, 0o600)
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as env_file:
            file_descriptor = None
            env_file.write(contents)
            env_file.flush()
            os.fsync(env_file.fileno())
        os.replace(temporary_path, path)
        directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
        directory_file_descriptor = os.open(parent, directory_flags)
        try:
            os.fsync(directory_file_descriptor)
        finally:
            try:
                os.close(directory_file_descriptor)
            except OSError:
                pass
        temporary_path = None
    except OSError as error:
        raise EnvMergeError(f"无法原子写入 env 文件 {path}: {error}") from error
    finally:
        if file_descriptor is not None:
            try:
                os.close(file_descriptor)
            except OSError:
                pass
        if temporary_path is not None:
            try:
                temporary_path.unlink()
            except OSError:
                pass


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="安全合并源生产配置与目标本地部署配置",
    )
    parser.add_argument("--source", required=True, type=Path, help="源 env 快照")
    parser.add_argument("--target", required=True, type=Path, help="目标现有 env")
    parser.add_argument("--output", required=True, type=Path, help="合并输出路径")
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        source_values = parse_env_file(arguments.source)
        target_values = parse_env_file(arguments.target)
        merged_values = merge_env_values(source_values, target_values)
        atomic_write(arguments.output, serialize_env(merged_values))
    except EnvMergeError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
