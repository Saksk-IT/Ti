from __future__ import annotations

from io import BytesIO
from pathlib import Path
import subprocess
import sys
import tarfile

import pytest

from tests.production_migration_test_support import (
    REPO_ROOT,
    load_python_helper,
    run_python_helper,
)


BUNDLE_MEMBERS = (
    "database.dump",
    "database-summary.txt",
    "redis.tar.gz",
    "uploads.tar.gz",
    "instance.tar.gz",
    "source.env.production",
    "manifest.txt",
    "checksums.sha256",
)


def run_archive_validator(
    archive: Path,
    profile: str,
) -> subprocess.CompletedProcess[str]:
    return run_python_helper(
        "scripts/lib/validate_migration_archive.py",
        "--archive",
        str(archive),
        "--profile",
        profile,
    )


def write_archive(
    path: Path,
    members: list[tuple[str, bytes]],
) -> None:
    with tarfile.open(path, mode="w:gz") as archive:
        for name, member_type in members:
            member = tarfile.TarInfo(name=name)
            member.type = member_type
            if member_type == tarfile.REGTYPE:
                contents = f"contents:{name}".encode()
                member.size = len(contents)
                archive.addfile(member, BytesIO(contents))
            else:
                member.size = 0
                if member_type in {tarfile.SYMTYPE, tarfile.LNKTYPE}:
                    member.linkname = "database.dump"
                archive.addfile(member)


def write_extended_archive(
    path: Path,
    member_name: str,
    archive_format: int,
    *,
    pax_headers: dict[str, str] | None = None,
) -> None:
    contents = b"extended-metadata-test"
    member = tarfile.TarInfo(member_name)
    member.size = len(contents)
    member.pax_headers = pax_headers or {}
    with tarfile.open(path, mode="w:gz", format=archive_format) as archive:
        archive.addfile(member, BytesIO(contents))


def regular_members(*names: str) -> list[tuple[str, bytes]]:
    return [(name, tarfile.REGTYPE) for name in names]


def test_archive_bundle_accepts_exact_regular_file_layout(tmp_path: Path) -> None:
    archive = tmp_path / "migration-bundle.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))

    result = run_archive_validator(archive, "bundle")

    assert result.returncode == 0, result.stderr


def test_archive_validator_only_inspects_and_never_extracts_members(tmp_path: Path) -> None:
    archive = tmp_path / "migration-bundle.tar.gz"
    execution_directory = tmp_path / "validator-cwd"
    execution_directory.mkdir()
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    marker = execution_directory / "database.dump"
    assert not marker.exists()

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "scripts/lib/validate_migration_archive.py"),
            "--archive",
            str(archive),
            "--profile",
            "bundle",
        ],
        cwd=execution_directory,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert not marker.exists()
    assert list(execution_directory.iterdir()) == []
    for member_name in BUNDLE_MEMBERS:
        assert not (execution_directory / member_name).exists()


def test_archive_validator_rejects_oversized_archive_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "oversized-bundle.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    monkeypatch.setattr(helper, "MAX_ARCHIVE_FILE_SIZE_BYTES", 1, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="归档文件过大"):
        helper.validate_archive(archive, "bundle")


def test_archive_validator_rejects_excessive_member_count(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "too-many-members.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    monkeypatch.setattr(helper, "MAX_ARCHIVE_MEMBERS", 6, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="归档成员数量过多"):
        helper.validate_archive(archive, "bundle")


def test_archive_validator_rejects_oversized_single_member_declaration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "large-member.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    monkeypatch.setattr(helper, "MAX_MEMBER_SIZE_BYTES", 1, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="单成员声明大小超限"):
        helper.validate_archive(archive, "bundle")


def test_archive_validator_rejects_oversized_total_member_declaration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "large-total.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    monkeypatch.setattr(helper, "MAX_TOTAL_MEMBER_SIZE_BYTES", 1, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="成员声明总大小超限"):
        helper.validate_archive(archive, "bundle")


def test_archive_validator_limits_member_name_by_utf8_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "long-name.tar.gz"
    unicode_member_name = "redis/题题题题"
    assert len(unicode_member_name) < len(unicode_member_name.encode("utf-8"))
    write_archive(
        archive,
        [("redis", tarfile.DIRTYPE), (unicode_member_name, tarfile.REGTYPE)],
    )
    monkeypatch.setattr(helper, "MAX_MEMBER_NAME_BYTES", 12, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="归档成员名称过长"):
        helper.validate_archive(archive, "redis")


def test_archive_validator_uses_bounded_decompressed_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "streamed-bundle.tar.gz"
    write_archive(archive, regular_members(*BUNDLE_MEMBERS))
    opened_modes: list[str] = []
    guarded_streams: list[object] = []
    real_tar_file = helper.tarfile.TarFile

    def recording_tar_file(*args: object, **kwargs: object) -> tarfile.TarFile:
        opened_modes.append(kwargs["mode"])
        guarded_streams.append(kwargs["fileobj"])
        return real_tar_file(*args, **kwargs)

    monkeypatch.setattr(helper.tarfile, "TarFile", recording_tar_file)

    helper.validate_archive(archive, "bundle")

    assert opened_modes == ["r"]
    assert len(guarded_streams) == 1
    assert isinstance(guarded_streams[0], helper.BoundedMetadataReader)


def test_archive_metadata_reader_rejects_cumulative_small_reads(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    reader = helper.BoundedMetadataReader(BytesIO(b"abcdefgh"))
    monkeypatch.setattr(helper, "MAX_METADATA_READ_BYTES", 4)
    monkeypatch.setattr(
        helper,
        "MAX_TOTAL_DECOMPRESSED_READ_BYTES",
        6,
        raising=False,
    )

    assert reader.read(4) == b"abcd"
    with pytest.raises(helper.ArchiveValidationError, match="累计解压读取超限"):
        reader.read(3)


def test_archive_validator_rejects_oversized_header_before_requesting_next(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    oversized_member = tarfile.TarInfo("redis/oversized.bin")
    oversized_member.size = 2

    class HeaderIterator:
        def __init__(self) -> None:
            self.requests = 0

        def __iter__(self) -> HeaderIterator:
            return self

        def __next__(self) -> tarfile.TarInfo:
            self.requests += 1
            if self.requests == 1:
                return oversized_member
            raise AssertionError("validator requested the next header")

    headers = HeaderIterator()
    monkeypatch.setattr(helper, "MAX_MEMBER_SIZE_BYTES", 1)

    with pytest.raises(helper.ArchiveValidationError, match="单成员声明大小超限"):
        helper.validate_archive_members(headers, "redis")

    assert headers.requests == 1


@pytest.mark.parametrize(
    ("archive_format", "member_name", "pax_headers"),
    [
        (tarfile.PAX_FORMAT, "redis/" + "p" * 3000, None),
        (tarfile.GNU_FORMAT, "redis/" + "g" * 3000, None),
    ],
    ids=["pax-long-path", "gnu-longname"],
)
def test_archive_validator_rejects_oversized_hidden_metadata(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    archive_format: int,
    member_name: str,
    pax_headers: dict[str, str] | None,
) -> None:
    helper = load_python_helper("scripts/lib/validate_migration_archive.py")
    archive = tmp_path / "hidden-metadata.tar.gz"
    write_extended_archive(
        archive,
        member_name,
        archive_format,
        pax_headers=pax_headers,
    )
    monkeypatch.setattr(helper, "MAX_METADATA_READ_BYTES", 1024, raising=False)

    with pytest.raises(helper.ArchiveValidationError, match="扩展元数据读取超限"):
        helper.validate_archive(archive, "redis")


def test_archive_validator_accepts_small_pax_and_checks_final_member(tmp_path: Path) -> None:
    archive = tmp_path / "small-pax.tar.gz"
    write_extended_archive(
        archive,
        "redis/data.bin",
        tarfile.PAX_FORMAT,
        pax_headers={"comment": "small-pax-header"},
    )

    result = run_archive_validator(archive, "redis")

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("unsafe_name", "replaced_name"),
    [
        ("/database.dump", "database.dump"),
        ("../database.dump", "database.dump"),
        ("nested/../../database.dump", "database.dump"),
    ],
)
def test_archive_bundle_rejects_absolute_and_traversal_paths(
    tmp_path: Path,
    unsafe_name: str,
    replaced_name: str,
) -> None:
    archive = tmp_path / "unsafe-bundle.tar.gz"
    names = [unsafe_name if name == replaced_name else name for name in BUNDLE_MEMBERS]
    write_archive(archive, regular_members(*names))

    result = run_archive_validator(archive, "bundle")

    assert result.returncode != 0


def test_archive_bundle_rejects_duplicate_members(tmp_path: Path) -> None:
    archive = tmp_path / "duplicate-bundle.tar.gz"
    write_archive(
        archive,
        regular_members(*BUNDLE_MEMBERS, "database.dump"),
    )

    result = run_archive_validator(archive, "bundle")

    assert result.returncode != 0


def test_archive_bundle_rejects_unexpected_members(tmp_path: Path) -> None:
    archive = tmp_path / "unexpected-bundle.tar.gz"
    write_archive(
        archive,
        regular_members(*BUNDLE_MEMBERS, "unexpected.txt"),
    )

    result = run_archive_validator(archive, "bundle")

    assert result.returncode != 0


def test_archive_bundle_rejects_missing_required_member(tmp_path: Path) -> None:
    archive = tmp_path / "incomplete-bundle.tar.gz"
    write_archive(
        archive,
        regular_members(*(name for name in BUNDLE_MEMBERS if name != "manifest.txt")),
    )

    result = run_archive_validator(archive, "bundle")

    assert result.returncode != 0


@pytest.mark.parametrize(
    "unsafe_type",
    [
        tarfile.SYMTYPE,
        tarfile.LNKTYPE,
        tarfile.FIFOTYPE,
        tarfile.CHRTYPE,
        tarfile.BLKTYPE,
        b"s",
    ],
    ids=["symlink", "hardlink", "fifo", "char-device", "block-device", "socket"],
)
def test_archive_bundle_rejects_non_regular_member_types(
    tmp_path: Path,
    unsafe_type: bytes,
) -> None:
    archive = tmp_path / "special-bundle.tar.gz"
    members = [
        (name, unsafe_type if name == "database.dump" else tarfile.REGTYPE)
        for name in BUNDLE_MEMBERS
    ]
    write_archive(archive, members)

    result = run_archive_validator(archive, "bundle")

    assert result.returncode != 0


@pytest.mark.parametrize("profile", ["redis", "uploads", "instance"])
def test_archive_inner_profile_accepts_only_its_prefix(
    tmp_path: Path,
    profile: str,
) -> None:
    archive = tmp_path / f"{profile}.tar.gz"
    write_archive(
        archive,
        [
            (profile, tarfile.DIRTYPE),
            (f"{profile}/nested", tarfile.DIRTYPE),
            (f"{profile}/nested/data.bin", tarfile.REGTYPE),
            (f"{profile}/.hidden", tarfile.REGTYPE),
        ],
    )

    result = run_archive_validator(archive, profile)

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("profile", ["redis", "uploads", "instance"])
def test_archive_inner_profile_rejects_files_outside_its_prefix(
    tmp_path: Path,
    profile: str,
) -> None:
    archive = tmp_path / f"wrong-prefix-{profile}.tar.gz"
    write_archive(
        archive,
        regular_members(f"{profile}/valid.bin", "other/unexpected.bin"),
    )

    result = run_archive_validator(archive, profile)

    assert result.returncode != 0


@pytest.mark.parametrize("profile", ["redis", "uploads", "instance"])
def test_archive_inner_profile_rejects_prefix_name_as_regular_file(
    tmp_path: Path,
    profile: str,
) -> None:
    archive = tmp_path / f"root-file-{profile}.tar.gz"
    write_archive(archive, regular_members(profile))

    result = run_archive_validator(archive, profile)

    assert result.returncode != 0


@pytest.mark.parametrize("profile", ["redis", "uploads", "instance"])
def test_archive_inner_profile_rejects_empty_archive(
    tmp_path: Path,
    profile: str,
) -> None:
    archive = tmp_path / f"empty-{profile}.tar.gz"
    write_archive(archive, [])

    result = run_archive_validator(archive, profile)

    assert result.returncode != 0
