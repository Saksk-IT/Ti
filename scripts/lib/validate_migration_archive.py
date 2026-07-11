#!/usr/bin/env python3
"""Validate migration tar metadata without extracting archive contents."""

from __future__ import annotations

import argparse
import bz2
from collections.abc import Iterable
from contextlib import contextmanager
import gzip
import lzma
from pathlib import Path, PurePosixPath
import sys
import tarfile
from typing import BinaryIO, Iterator


BUNDLE_MEMBERS = frozenset(
    {
        "database.dump",
        "database-summary.txt",
        "redis.tar.gz",
        "uploads.tar.gz",
        "instance.tar.gz",
        "source.env.production",
        "manifest.txt",
        "checksums.sha256",
    }
)
VALID_PROFILES = ("bundle", "redis", "uploads", "instance")
GIBIBYTE = 1024**3
MAX_ARCHIVE_FILE_SIZE_BYTES = 100 * GIBIBYTE
MAX_ARCHIVE_MEMBERS = 200_000
MAX_MEMBER_SIZE_BYTES = 100 * GIBIBYTE
MAX_TOTAL_MEMBER_SIZE_BYTES = 500 * GIBIBYTE
MAX_MEMBER_NAME_BYTES = 4096
MAX_METADATA_READ_BYTES = 8 * 1024 * 1024
MAX_TOTAL_DECOMPRESSED_READ_BYTES = 256 * 1024 * 1024


class ArchiveValidationError(ValueError):
    """Raised when archive metadata violates the migration contract."""


class BoundedMetadataReader:
    """Proxy a decompressed stream while rejecting oversized single reads."""

    def __init__(self, stream: BinaryIO) -> None:
        self._stream = stream
        self._total_bytes_read = 0

    def read(self, size: int = -1) -> bytes:
        if size < 0 or size > MAX_METADATA_READ_BYTES:
            raise ArchiveValidationError("扩展元数据读取超限")
        contents = self._stream.read(size)
        self._total_bytes_read += len(contents)
        if self._total_bytes_read > MAX_TOTAL_DECOMPRESSED_READ_BYTES:
            raise ArchiveValidationError("累计解压读取超限")
        return contents

    def seek(self, offset: int, whence: int = 0) -> int:
        return self._stream.seek(offset, whence)

    def tell(self) -> int:
        return self._stream.tell()

    def __getattr__(self, name: str) -> object:
        return getattr(self._stream, name)


@contextmanager
def open_decompressed_stream(archive_path: Path) -> Iterator[BinaryIO]:
    with archive_path.open("rb") as raw_stream:
        magic = raw_stream.read(6)
        raw_stream.seek(0)
        if magic.startswith(b"\x1f\x8b"):
            decompressed_stream: BinaryIO = gzip.GzipFile(
                fileobj=raw_stream,
                mode="rb",
            )
        elif magic.startswith(b"BZh"):
            decompressed_stream = bz2.BZ2File(raw_stream, mode="rb")
        elif magic.startswith(b"\xfd7zXZ\x00"):
            decompressed_stream = lzma.LZMAFile(raw_stream, mode="rb")
        else:
            yield raw_stream
            return

        with decompressed_stream:
            yield decompressed_stream


def normalize_member_name(raw_name: str) -> str:
    if not raw_name:
        raise ArchiveValidationError("归档包含空成员名")
    try:
        name_size = len(raw_name.encode("utf-8"))
    except UnicodeError as error:
        raise ArchiveValidationError("归档成员名称不是有效 UTF-8") from error
    if name_size > MAX_MEMBER_NAME_BYTES:
        raise ArchiveValidationError("归档成员名称过长")

    member_path = PurePosixPath(raw_name)
    if member_path.is_absolute():
        raise ArchiveValidationError(f"归档包含绝对路径: {raw_name}")
    if ".." in member_path.parts:
        raise ArchiveValidationError(f"归档包含路径穿越成员: {raw_name}")

    normalized_name = str(member_path)
    if normalized_name in {"", "."}:
        raise ArchiveValidationError(f"归档包含无效成员名: {raw_name}")
    return normalized_name


def validate_member_type(member: tarfile.TarInfo, normalized_name: str) -> None:
    if not (member.isreg() or member.isdir()):
        raise ArchiveValidationError(f"归档包含不允许的成员类型: {normalized_name}")


def validate_bundle_member(member: tarfile.TarInfo, normalized_name: str) -> None:
    if not member.isreg():
        raise ArchiveValidationError(f"迁移包成员必须是普通文件: {normalized_name}")
    if normalized_name not in BUNDLE_MEMBERS:
        raise ArchiveValidationError(f"迁移包包含意外成员: {normalized_name}")


def validate_inner_member(
    member: tarfile.TarInfo,
    normalized_name: str,
    profile: str,
) -> None:
    member_path = PurePosixPath(normalized_name)
    if not member_path.parts or member_path.parts[0] != profile:
        raise ArchiveValidationError(
            f"{profile} 归档包含前缀之外的成员: {normalized_name}"
        )
    if len(member_path.parts) == 1 and not member.isdir():
        raise ArchiveValidationError(f"{profile} 根成员必须是目录")


def validate_archive_members(
    members: Iterable[tarfile.TarInfo],
    profile: str,
) -> tuple[str, ...]:
    normalized_names: list[str] = []
    seen_names: set[str] = set()
    total_declared_size = 0

    for member_count, member in enumerate(members, start=1):
        if member_count > MAX_ARCHIVE_MEMBERS:
            raise ArchiveValidationError("归档成员数量过多")

        normalized_name = normalize_member_name(member.name)
        if normalized_name in seen_names:
            raise ArchiveValidationError("归档包含重复成员")
        validate_member_type(member, normalized_name)

        if member.size < 0:
            raise ArchiveValidationError(
                f"归档成员声明大小无效: {normalized_name}"
            )
        if member.size > MAX_MEMBER_SIZE_BYTES:
            raise ArchiveValidationError(
                f"单成员声明大小超限: {normalized_name}"
            )
        total_declared_size += member.size
        if total_declared_size > MAX_TOTAL_MEMBER_SIZE_BYTES:
            raise ArchiveValidationError("成员声明总大小超限")

        if profile == "bundle":
            validate_bundle_member(member, normalized_name)
        else:
            validate_inner_member(member, normalized_name, profile)
        seen_names.add(normalized_name)
        normalized_names.append(normalized_name)

    names = tuple(normalized_names)
    if profile == "bundle":
        if seen_names != BUNDLE_MEMBERS:
            missing_names = sorted(BUNDLE_MEMBERS - seen_names)
            raise ArchiveValidationError(
                f"迁移包缺少必需成员: {', '.join(missing_names)}"
            )
    elif not names:
        raise ArchiveValidationError(f"{profile} 归档不能为空")
    return names


def iter_tar_headers(archive: tarfile.TarFile) -> Iterator[tarfile.TarInfo]:
    while True:
        member = archive.next()
        if member is None:
            return
        archive.members.clear()
        yield member


def validate_archive(archive_path: Path, profile: str) -> None:
    try:
        if archive_path.stat().st_size > MAX_ARCHIVE_FILE_SIZE_BYTES:
            raise ArchiveValidationError(f"归档文件过大: {archive_path}")
        with open_decompressed_stream(archive_path) as decompressed_stream:
            guarded_stream = BoundedMetadataReader(decompressed_stream)
            with tarfile.TarFile(fileobj=guarded_stream, mode="r") as archive:
                validate_archive_members(iter_tar_headers(archive), profile)
    except (EOFError, OSError, lzma.LZMAError, tarfile.TarError) as error:
        raise ArchiveValidationError(f"无法读取归档 {archive_path}: {error}") from error


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="安全检查生产数据迁移归档")
    parser.add_argument("--archive", required=True, type=Path, help="待检查归档")
    parser.add_argument(
        "--profile",
        required=True,
        choices=VALID_PROFILES,
        help="归档布局类型",
    )
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    try:
        validate_archive(arguments.archive, arguments.profile)
    except ArchiveValidationError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
