# -*- coding: utf-8 -*-
"""生成与 scripts/restore.sh 兼容的私有业务数据归档。"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tarfile
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping, Optional
from urllib.parse import parse_qs, unquote, urlsplit

from flask import current_app


_COMPOSE_FILE_PATTERN = re.compile(r"^(?:docker-)?compose(?:\..+)?\.ya?ml$")


class BackupArchiveError(RuntimeError):
    """备份归档配置或生成失败。"""


@dataclass(frozen=True)
class BackupArchiveResult:
    """归档产物元数据。"""

    path: Path
    filename: str
    size_bytes: int
    sha256: str


@dataclass(frozen=True)
class _PostgresTarget:
    host: str
    port: int
    username: str
    password: str
    database: str
    sslmode: str


def _parse_database_url(database_url: str) -> _PostgresTarget:
    parsed = urlsplit(str(database_url or ""))
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise BackupArchiveError("备份仅支持 PostgreSQL 数据库")
    host = parsed.hostname or ""
    username = unquote(parsed.username or "")
    database = unquote(parsed.path.lstrip("/"))
    if not host or not username or not database:
        raise BackupArchiveError("PostgreSQL 连接配置不完整")
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise BackupArchiveError("PostgreSQL 端口配置无效") from exc
    sslmode = parse_qs(parsed.query).get("sslmode", [""])[0]
    return _PostgresTarget(
        host=host,
        port=port,
        username=username,
        password=unquote(parsed.password or ""),
        database=database,
        sslmode=sslmode,
    )


def _safe_job_suffix(job_id: str) -> str:
    compact = "".join(char for char in str(job_id) if char.lower() in "0123456789abcdef")
    if len(compact) < 8:
        raise BackupArchiveError("备份任务 ID 无效")
    return compact[:8].lower()


def _copy_regular_tree(source: Optional[Path], destination: Path) -> bool:
    destination.mkdir(mode=0o700, parents=True, exist_ok=False)
    if source is None or not source.is_dir() or source.is_symlink():
        return False
    for current, directories, filenames in os.walk(source, followlinks=False):
        current_path = Path(current)
        directories[:] = [
            name
            for name in directories
            if not (current_path / name).is_symlink()
            and not _is_excluded_name(name, is_directory=True)
        ]
        relative = current_path.relative_to(source)
        target_dir = destination / relative
        target_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        for filename in filenames:
            if _is_excluded_name(filename, is_directory=False):
                continue
            candidate = current_path / filename
            try:
                mode = candidate.lstat().st_mode
            except OSError:
                continue
            if stat.S_ISREG(mode):
                shutil.copy2(candidate, target_dir / filename, follow_symlinks=False)
    return True


def _is_excluded_name(name: str, *, is_directory: bool) -> bool:
    lowered = str(name).lower()
    if lowered == ".env" or lowered.startswith(".env."):
        return True
    if is_directory and lowered in {"redis", "log", "logs"}:
        return True
    if not is_directory and lowered.endswith(".log"):
        return True
    return bool(_COMPOSE_FILE_PATTERN.fullmatch(lowered))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class BackupArchiveService:
    """从服务端构造的数据源生成最小可恢复归档。"""

    def __init__(
        self,
        *,
        database_url: str,
        uploads_dir: Path | str | None,
        instance_dir: Path | str | None,
        temp_root: Path | str | None = None,
        pg_dump_path: str = "pg_dump",
        timeout: int = 900,
        runner: Callable[..., Any] = subprocess.run,
        now: Callable[[], datetime] = datetime.utcnow,
        base_env: Optional[Mapping[str, str]] = None,
    ):
        self._database = _parse_database_url(database_url)
        self._uploads_dir = Path(uploads_dir) if uploads_dir is not None else None
        self._instance_dir = Path(instance_dir) if instance_dir is not None else None
        self._temp_root = Path(temp_root) if temp_root is not None else None
        self._pg_dump_path = str(pg_dump_path)
        self._timeout = max(1, int(timeout))
        self._runner = runner
        self._now = now
        self._base_env = dict(base_env) if base_env is not None else dict(os.environ)
        self._owned_work_dirs: tuple[Path, ...] = ()

    @classmethod
    def from_environment(cls) -> "BackupArchiveService":
        data_dir = Path(str(current_app.config["DATA_DIR"]))
        return cls(
            database_url=str(current_app.config["SQLALCHEMY_DATABASE_URI"]),
            uploads_dir=Path(str(current_app.config["UPLOAD_FOLDER"])),
            instance_dir=data_dir / "instance",
            temp_root=os.environ.get("BACKUP_TEMP_DIR") or None,
            pg_dump_path=os.environ.get("PG_DUMP_PATH", "pg_dump"),
            timeout=int(os.environ.get("BACKUP_PG_DUMP_TIMEOUT", "900") or 900),
        )

    def _pg_environment(self) -> dict[str, str]:
        allowed = ("PATH", "LANG", "LC_ALL", "TZ", "SYSTEMROOT", "WINDIR")
        environment = {
            key: str(self._base_env[key]) for key in allowed if self._base_env.get(key)
        }
        environment["PGPASSWORD"] = self._database.password
        if self._database.sslmode:
            environment["PGSSLMODE"] = self._database.sslmode
        return environment

    def _dump_database(self, output_path: Path) -> None:
        command = [
            self._pg_dump_path,
            "--host",
            self._database.host,
            "--port",
            str(self._database.port),
            "--username",
            self._database.username,
            "--dbname",
            self._database.database,
            "--no-password",
        ]
        with output_path.open("wb") as output:
            self._runner(
                command,
                shell=False,
                check=True,
                timeout=self._timeout,
                env=self._pg_environment(),
                stdout=output,
                stderr=subprocess.PIPE,
            )
        output_path.chmod(0o600)

    def _write_manifest(self, archive_root: Path, timestamp: datetime) -> None:
        files = sorted(
            str(path.relative_to(archive_root))
            for path in archive_root.rglob("*")
            if path.is_file() and not path.is_symlink()
        )
        lines = [
            f"备份时间: {timestamp.isoformat()}",
            "备份内容:",
            "- PostgreSQL: database.sql",
            "- 上传文件: uploads/（目录存在时）",
            "- 实例数据: instance/（目录存在时）",
            "明确排除: Redis、日志、环境文件、Compose 配置",
            "",
            "文件列表:",
            *files,
            "",
        ]
        manifest = archive_root / "MANIFEST.txt"
        manifest.write_text("\n".join(lines), encoding="utf-8")
        manifest.chmod(0o600)

    def create_archive(self, job_id: str) -> BackupArchiveResult:
        timestamp = self._now()
        basename = f"backup_{timestamp:%Y%m%d_%H%M%S}_{_safe_job_suffix(job_id)}"
        if self._temp_root is not None:
            self._temp_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        work_dir = Path(
            tempfile.mkdtemp(prefix="ti-backup-", dir=self._temp_root)
        )
        work_dir.chmod(0o700)
        self._owned_work_dirs = (*self._owned_work_dirs, work_dir.resolve())
        archive_root = work_dir / basename
        archive_path = work_dir / f"{basename}.tar.gz"
        try:
            archive_root.mkdir(mode=0o700)
            self._dump_database(archive_root / "database.sql")
            _copy_regular_tree(self._uploads_dir, archive_root / "uploads")
            _copy_regular_tree(self._instance_dir, archive_root / "instance")
            self._write_manifest(archive_root, timestamp)
            with tarfile.open(archive_path, mode="w:gz", dereference=False) as archive:
                archive.add(archive_root, arcname=basename, recursive=True)
            archive_path.chmod(0o600)
            shutil.rmtree(archive_root)
            return BackupArchiveResult(
                path=archive_path,
                filename=archive_path.name,
                size_bytes=archive_path.stat().st_size,
                sha256=_sha256(archive_path),
            )
        except Exception:
            shutil.rmtree(work_dir, ignore_errors=True)
            self._owned_work_dirs = tuple(
                owned for owned in self._owned_work_dirs if owned != work_dir.resolve()
            )
            raise

    def cleanup_archive(self, archive_path: Path | str) -> None:
        path = Path(archive_path)
        parent = path.parent.resolve()
        if parent not in self._owned_work_dirs:
            return
        self._owned_work_dirs = tuple(
            owned for owned in self._owned_work_dirs if owned != parent
        )
        shutil.rmtree(parent, ignore_errors=True)
