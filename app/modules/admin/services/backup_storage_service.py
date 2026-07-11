# -*- coding: utf-8 -*-
"""Cloudflare R2 备份对象存储操作。"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Optional

from app.modules.admin.services.backup_config_service import (
    BackupConfigValidationError,
    _validate_bucket,
    _validate_endpoint,
    _validate_prefix,
)


logger = logging.getLogger(__name__)
_ARCHIVE_NAME_PATTERN = re.compile(
    r"^backup_\d{8}_\d{6}_[0-9a-fA-F]{8}\.tar\.gz$"
)
_MULTIPART_CHUNK_BYTES = 8 * 1024 * 1024
_MULTIPART_CONCURRENCY = 2
_MULTIPART_IO_QUEUE = 4


class BackupStorageError(RuntimeError):
    """R2 操作或边界校验失败。"""


@dataclass(frozen=True)
class BackupUploadResult:
    """已上传并完成远端大小校验的对象。"""

    object_key: str
    size_bytes: int


def _storage_config(config: Mapping[str, Any]) -> dict[str, str]:
    if not isinstance(config, Mapping):
        raise BackupStorageError("备份存储配置无效")
    try:
        endpoint = _validate_endpoint(config.get("endpoint"))
        bucket = _validate_bucket(config.get("bucket"))
        prefix = _validate_prefix(config.get("prefix"))
    except BackupConfigValidationError as exc:
        raise BackupStorageError("备份存储配置未经有效校验") from exc
    region = str(config.get("region") or "").strip()
    access_key_id = str(config.get("access_key_id") or "").strip()
    secret_access_key = str(config.get("secret_access_key") or "").strip()
    if region != "auto":
        raise BackupStorageError("备份存储区域配置无效")
    if not access_key_id or not secret_access_key or "*" in (
        access_key_id + secret_access_key
    ):
        raise BackupStorageError("备份存储凭据未完整配置")
    return {
        "endpoint": endpoint,
        "region": region,
        "bucket": bucket,
        "prefix": f"{prefix.rstrip('/')}/",
        "access_key_id": access_key_id,
        "secret_access_key": secret_access_key,
    }


class BackupStorageService:
    """只在当前 Bucket 和服务端配置前缀内操作备份对象。"""

    def __init__(
        self,
        config: Mapping[str, Any],
        *,
        client: Optional[Any] = None,
        transfer_config: Optional[Any] = None,
    ):
        validated = _storage_config(config)
        self._endpoint = validated["endpoint"]
        self._region = validated["region"]
        self._bucket = validated["bucket"]
        self._prefix = validated["prefix"]
        self._access_key_id = validated["access_key_id"]
        self._secret_access_key = validated["secret_access_key"]
        self._client = client
        self._transfer_config = transfer_config

    @property
    def bucket(self) -> str:
        return self._bucket

    @property
    def prefix(self) -> str:
        return self._prefix

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
            except ImportError as exc:
                raise BackupStorageError("R2 客户端依赖尚未安装") from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint,
                region_name=self._region,
                aws_access_key_id=self._access_key_id,
                aws_secret_access_key=self._secret_access_key,
            )
        return self._client

    def _get_transfer_config(self) -> Any:
        if self._transfer_config is None:
            try:
                from boto3.s3.transfer import TransferConfig
            except ImportError as exc:
                raise BackupStorageError("R2 客户端依赖尚未安装") from exc
            self._transfer_config = TransferConfig(
                multipart_threshold=_MULTIPART_CHUNK_BYTES,
                multipart_chunksize=_MULTIPART_CHUNK_BYTES,
                max_concurrency=_MULTIPART_CONCURRENCY,
                max_io_queue=_MULTIPART_IO_QUEUE,
                use_threads=True,
            )
        return self._transfer_config

    def _require_current_key(self, object_key: str) -> str:
        key = str(object_key or "")
        if (
            not key.startswith(self._prefix)
            or key == self._prefix
            or "\\" in key
            or any(part in {"", ".", ".."} for part in key.split("/"))
        ):
            raise BackupStorageError("对象不属于当前备份前缀")
        return key

    def _archive_key(self, archive_path: Path) -> str:
        if not _ARCHIVE_NAME_PATTERN.fullmatch(archive_path.name):
            raise BackupStorageError("备份归档文件名不是服务端生成格式")
        return self._require_current_key(f"{self._prefix}{archive_path.name}")

    def test_connection(self) -> None:
        """写入固定健康检查前缀，并保证尝试删除测试对象。"""
        key = f"{self._prefix}.healthcheck/{uuid.uuid4().hex}.txt"
        client = self._get_client()
        put_failed = False
        try:
            client.put_object(Bucket=self._bucket, Key=key, Body=b"ok")
        except Exception:
            put_failed = True
            raise
        finally:
            try:
                client.delete_object(Bucket=self._bucket, Key=key)
            except Exception:
                if not put_failed:
                    raise
                logger.warning("R2 健康检查对象清理失败", exc_info=True)

    def upload_file(self, archive_path: Path | str) -> BackupUploadResult:
        path = Path(archive_path)
        if not path.is_file():
            raise BackupStorageError("本地备份归档不存在")
        key = self._archive_key(path)
        local_size = path.stat().st_size
        client = self._get_client()
        try:
            client.upload_file(
                str(path),
                self._bucket,
                key,
                Config=self._get_transfer_config(),
            )
            metadata = client.head_object(Bucket=self._bucket, Key=key)
            remote_size = int(metadata["ContentLength"])
            if remote_size != local_size:
                raise BackupStorageError("R2 对象大小校验失败")
        except Exception as exc:
            try:
                client.delete_object(Bucket=self._bucket, Key=key)
            except Exception:
                logger.warning("R2 未完成上传对象清理失败", exc_info=True)
            if isinstance(exc, (KeyError, TypeError, ValueError)):
                raise BackupStorageError("R2 对象大小响应无效") from exc
            raise
        return BackupUploadResult(object_key=key, size_bytes=local_size)

    def generate_presigned_url(self, object_key: str) -> str:
        key = self._require_current_key(object_key)
        return str(
            self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=300,
            )
        )

    def delete_object(self, object_key: str) -> None:
        key = self._require_current_key(object_key)
        self._get_client().delete_object(Bucket=self._bucket, Key=key)
