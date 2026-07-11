# -*- coding: utf-8 -*-
"""Cloudflare R2 数据库备份配置服务。"""

from __future__ import annotations

import base64
import hashlib
import os
import re
from typing import Any, Dict, Mapping, Optional, Set
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken
from flask import current_app
from sqlalchemy import select, text

from app.core.extensions import db
from app.models.system import SystemConfig
from app.modules.admin.services.system_config_service import (
    _cache_clear,
)


_ENCRYPTED_PREFIX = "enc:backup:v1:"
_R2_HOST_PATTERN = re.compile(
    r"^[0-9a-f]{32}(?:\.(?:eu|fedramp))?\.r2\.cloudflarestorage\.com$"
)
_BUCKET_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$")
_PREFIX_SEGMENT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_MASK = "***"
_STORAGE_IDENTITY_LOCK_KEY = 1414087243

_DEFAULTS: Dict[str, Any] = {
    "endpoint": "",
    "region": "auto",
    "bucket": "",
    "prefix": "backups/",
    "schedule_enabled": False,
    "cron_expression": "0 2 * * *",
    "retention_days": 14,
    "max_backups": 3,
}
_PLAIN_FIELDS = tuple(_DEFAULTS)
_CREDENTIAL_FIELDS = ("access_key_id", "secret_access_key")
_STORAGE_IDENTITY_FIELDS = ("endpoint", "bucket", "prefix")
_DESCRIPTIONS = {
    "endpoint": "Cloudflare R2 S3 endpoint",
    "region": "Cloudflare R2 region（固定 auto）",
    "bucket": "Cloudflare R2 bucket",
    "prefix": "Cloudflare R2 对象前缀",
    "access_key_id": "Cloudflare R2 Access Key ID（加密）",
    "secret_access_key": "Cloudflare R2 Secret Access Key（加密）",
    "schedule_enabled": "数据库定时备份开关",
    "cron_expression": "数据库定时备份 cron",
    "retention_days": "数据库备份保留天数",
    "max_backups": "数据库备份最大保留份数",
}


class BackupConfigError(RuntimeError):
    """备份配置读取或加解密失败。"""


class BackupConfigValidationError(ValueError):
    """备份配置校验失败。"""


def _config_key(field: str) -> str:
    return f"backup_{field}"


def _get_app_config(name: str) -> str:
    try:
        return str(current_app.config.get(name) or "").strip()
    except RuntimeError:
        return ""


def _secret_material() -> str:
    secret = os.environ.get("BACKUP_CREDENTIAL_SECRET", "").strip()
    if not secret:
        secret = _get_app_config("BACKUP_CREDENTIAL_SECRET")
    if not secret:
        secret = _get_app_config("SECRET_KEY")
    if not secret:
        secret = os.environ.get("SECRET_KEY", "").strip()
    if not secret:
        raise BackupConfigError("备份凭据加密密钥未配置")
    return secret


def _fernet() -> Fernet:
    material = f"ti-backup-credentials:{_secret_material()}".encode("utf-8")
    digest = hashlib.sha256(material).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt_credential(value: str) -> str:
    token = _fernet().encrypt(value.encode("utf-8")).decode("ascii")
    return f"{_ENCRYPTED_PREFIX}{token}"


def _decrypt_credential(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_ENCRYPTED_PREFIX):
        raise BackupConfigError("备份凭据格式无效，请重新保存凭据")
    try:
        token = value[len(_ENCRYPTED_PREFIX):].encode("ascii")
        return _fernet().decrypt(token).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise BackupConfigError("备份凭据解密失败，请重新保存凭据") from exc


def _mask_credential(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return _MASK
    return f"{value[:4]}****{value[-4:]}"


def _is_masked(value: str) -> bool:
    return bool(value) and "*" in value


def _stored_value(field: str) -> str:
    value = db.session.execute(
        select(SystemConfig.config_value).where(
            SystemConfig.config_key == _config_key(field)
        )
    ).scalar_one_or_none()
    return str(value or "")


def _parse_bool(value: Any, field: str) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    raise BackupConfigValidationError(f"{field}: 必须为布尔值")


def _parse_int(value: Any, field: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool):
        raise BackupConfigValidationError(f"{field}: 必须为整数")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise BackupConfigValidationError(f"{field}: 必须为整数") from exc
    if str(value).strip() != str(parsed):
        raise BackupConfigValidationError(f"{field}: 必须为整数")
    if not minimum <= parsed <= maximum:
        raise BackupConfigValidationError(
            f"{field}: 必须在 {minimum} 到 {maximum} 之间"
        )
    return parsed


def _validate_endpoint(value: Any) -> str:
    endpoint = str(value or "").strip()
    if not endpoint or any(char.isspace() for char in endpoint):
        raise BackupConfigValidationError("endpoint: 请输入有效的 Cloudflare R2 地址")
    try:
        parsed = urlsplit(endpoint)
        port = parsed.port
    except ValueError as exc:
        raise BackupConfigValidationError("endpoint: 地址格式无效") from exc
    host = (parsed.hostname or "").lower()
    canonical_endpoint = f"https://{host}"
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or port is not None
        or parsed.path
        or parsed.query
        or parsed.fragment
        or not _R2_HOST_PATTERN.fullmatch(host)
        or endpoint != canonical_endpoint
    ):
        raise BackupConfigValidationError(
            "endpoint: 仅允许 Cloudflare R2 官方 HTTPS endpoint，且不能包含端口、路径或参数"
        )
    return endpoint


def _validate_bucket(value: Any) -> str:
    bucket = str(value or "").strip()
    if not _BUCKET_PATTERN.fullmatch(bucket):
        raise BackupConfigValidationError(
            "bucket: 需为 3-63 位小写字母、数字或连字符，且首尾必须为字母或数字"
        )
    return bucket


def _validate_prefix(value: Any) -> str:
    prefix = str(value or "").strip()
    if not prefix:
        return str(_DEFAULTS["prefix"])
    if (
        len(prefix) > 512
        or prefix.startswith("/")
        or "\\" in prefix
        or "//" in prefix
        or ".." in prefix
    ):
        raise BackupConfigValidationError("prefix: 对象前缀格式无效")
    segments = prefix[:-1].split("/") if prefix.endswith("/") else prefix.split("/")
    if not segments or any(
        segment in {".", ".."} or not _PREFIX_SEGMENT_PATTERN.fullmatch(segment)
        for segment in segments
    ):
        raise BackupConfigValidationError("prefix: 只能包含安全的对象路径片段")
    return prefix


def _cron_field_values(token: str, minimum: int, maximum: int) -> Set[int]:
    values: Set[int] = set()
    if not token or token.count("/") > 1:
        raise ValueError("invalid cron field")
    for item in token.split(","):
        if not item:
            raise ValueError("invalid cron list")
        base, separator, raw_step = item.partition("/")
        step = int(raw_step) if separator else 1
        if step < 1:
            raise ValueError("invalid cron step")
        if base == "*":
            start, end = minimum, maximum
        elif "-" in base:
            raw_start, raw_end = base.split("-", 1)
            start, end = int(raw_start), int(raw_end)
        else:
            start = int(base)
            end = maximum if separator else start
        if start < minimum or end > maximum or start > end:
            raise ValueError("cron value out of range")
        values.update(range(start, end + 1, step))
    if not values:
        raise ValueError("empty cron field")
    return values


def _validate_cron(value: Any) -> str:
    expression = " ".join(str(value or "").strip().split())
    fields = expression.split(" ") if expression else []
    if len(fields) != 5:
        raise BackupConfigValidationError("cron_expression: 必须是五段 cron 表达式")
    limits = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 7))
    try:
        parsed = [
            _cron_field_values(token, minimum, maximum)
            for token, (minimum, maximum) in zip(fields, limits)
        ]
    except (TypeError, ValueError) as exc:
        raise BackupConfigValidationError(
            "cron_expression: 仅支持有效的数字五段 cron 表达式"
        ) from exc
    if len(parsed[0]) != 1:
        raise BackupConfigValidationError(
            "cron_expression: 备份执行间隔不能短于 1 小时"
        )
    return expression


def _validate_config(data: Mapping[str, Any]) -> Dict[str, Any]:
    region = str(data.get("region") or "").strip()
    if region != "auto":
        raise BackupConfigValidationError("region: Cloudflare R2 region 必须为 auto")
    return {
        "endpoint": _validate_endpoint(data.get("endpoint")),
        "region": region,
        "bucket": _validate_bucket(data.get("bucket")),
        "prefix": _validate_prefix(data.get("prefix")),
        "schedule_enabled": _parse_bool(
            data.get("schedule_enabled"), "schedule_enabled"
        ),
        "cron_expression": _validate_cron(data.get("cron_expression")),
        "retention_days": _parse_int(
            data.get("retention_days"), "retention_days", 0, 3650
        ),
        "max_backups": _parse_int(data.get("max_backups"), "max_backups", 1, 100),
    }


def _serialize_plain_value(field: str, value: Any) -> str:
    if field == "schedule_enabled":
        return "true" if value else "false"
    return str(value)


def acquire_storage_identity_lock() -> None:
    """在 PostgreSQL 中串行化存储身份变更与新备份任务创建。"""
    bind = db.session.get_bind()
    if bind.dialect.name == "postgresql":
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": _STORAGE_IDENTITY_LOCK_KEY},
        )


class BackupConfigService:
    """读取、校验并安全保存 Cloudflare R2 备份配置。"""

    @staticmethod
    def get_config() -> Dict[str, Any]:
        raw = {field: _stored_value(field) for field in _PLAIN_FIELDS}
        plain = {
            "endpoint": raw["endpoint"] or _DEFAULTS["endpoint"],
            "region": raw["region"] or _DEFAULTS["region"],
            "bucket": raw["bucket"] or _DEFAULTS["bucket"],
            "prefix": raw["prefix"] if raw["prefix"] else _DEFAULTS["prefix"],
            "schedule_enabled": _parse_bool(
                raw["schedule_enabled"] or _DEFAULTS["schedule_enabled"],
                "schedule_enabled",
            ),
            "cron_expression": raw["cron_expression"] or _DEFAULTS["cron_expression"],
            "retention_days": _parse_int(
                raw["retention_days"] or _DEFAULTS["retention_days"],
                "retention_days",
                0,
                3650,
            ),
            "max_backups": _parse_int(
                raw["max_backups"] or _DEFAULTS["max_backups"],
                "max_backups",
                1,
                100,
            ),
        }
        encrypted_credentials = {
            field: _stored_value(field) for field in _CREDENTIAL_FIELDS
        }
        credentials = {
            field: _decrypt_credential(encrypted) if encrypted else ""
            for field, encrypted in encrypted_credentials.items()
        }
        return {
            **plain,
            "access_key_id": _mask_credential(credentials["access_key_id"]),
            "secret_access_key": _mask_credential(credentials["secret_access_key"]),
            "access_key_id_configured": bool(credentials["access_key_id"]),
            "secret_access_key_configured": bool(credentials["secret_access_key"]),
        }

    @staticmethod
    def get_runtime_config() -> Dict[str, Any]:
        """返回经校验且已解密的内部执行配置，不得用于 API 响应。"""
        public_config = BackupConfigService.get_config()
        validated = _validate_config(public_config)
        credentials = {
            field: _decrypt_credential(_stored_value(field))
            for field in _CREDENTIAL_FIELDS
        }
        missing = [field for field, value in credentials.items() if not value]
        if missing:
            raise BackupConfigError("备份存储凭据未完整配置")
        return {**validated, **credentials}

    @staticmethod
    def save_config(
        data: Mapping[str, Any], admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        if not isinstance(data, Mapping):
            raise BackupConfigValidationError("配置数据必须为对象")

        current = BackupConfigService.get_config()
        candidate = {
            field: data[field] if field in data else current[field]
            for field in _PLAIN_FIELDS
        }
        validated = _validate_config(candidate)
        identity_submitted = any(
            field in data for field in _STORAGE_IDENTITY_FIELDS
        )
        if identity_submitted:
            acquire_storage_identity_lock()
            db.session.expire_all()
            current = BackupConfigService.get_config()
            candidate = {
                field: data[field] if field in data else current[field]
                for field in _PLAIN_FIELDS
            }
            validated = _validate_config(candidate)
            identity_changed = any(
                validated[field] != current[field]
                for field in _STORAGE_IDENTITY_FIELDS
            )
            if identity_changed:
                from app.models.backup import BackupJob

                historical_exists = BackupJob.query.filter(
                    BackupJob.status.in_(
                        ("queued", "running", "completed", "deleting")
                    )
                ).first()
                if historical_exists is not None:
                    raise BackupConfigValidationError(
                        "存在活动任务或存储位置已有备份记录，请等待任务结束并删除现有备份记录后再修改 Endpoint、Bucket 或 Prefix"
                    )
        plain_updates = {
            field: _serialize_plain_value(field, validated[field])
            for field in _PLAIN_FIELDS
            if field in data
        }
        credential_updates = {
            field: _encrypt_credential(submitted)
            for field in _CREDENTIAL_FIELDS
            if (submitted := str(data.get(field) or "").strip())
            and not _is_masked(submitted)
        }
        updates = {**plain_updates, **credential_updates}

        try:
            for field, value in updates.items():
                config_key = _config_key(field)
                existing = SystemConfig.query.filter_by(config_key=config_key).first()
                if existing:
                    existing.config_value = value
                    existing.description = _DESCRIPTIONS[field]
                    existing.updated_by = admin_id
                    continue
                db.session.add(
                    SystemConfig(
                        config_key=config_key,
                        config_value=value,
                        description=_DESCRIPTIONS[field],
                        updated_by=admin_id,
                    )
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        _cache_clear()

        return BackupConfigService.get_config()
