# -*- coding: utf-8 -*-
"""Cloudflare R2 备份配置与任务管理 API。"""

from __future__ import annotations

from functools import wraps
import re
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
from uuid import UUID

from flask import current_app, g, request, session
from flask_limiter.errors import RateLimitExceeded

from app.core.extensions import limiter
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.modules.admin.services.backup_config_service import (
    BackupConfigError,
    BackupConfigService,
    BackupConfigValidationError,
)
from app.modules.admin.services.backup_job_service import (
    BackupJobConflictError,
    BackupJobError,
    BackupJobNotFoundError,
    BackupJobService,
)
from app.modules.admin.services.backup_storage_service import BackupStorageService

from ..api_bp import admin_api_bp


_CONFIG_FIELDS = frozenset(
    {
        "endpoint",
        "region",
        "bucket",
        "prefix",
        "access_key_id",
        "secret_access_key",
        "schedule_enabled",
        "cron_expression",
        "retention_days",
        "max_backups",
    }
)
_SAFE_REQUEST_ID_PATTERN = re.compile(r"^[A-Fa-f0-9]{16,64}$")

# 模块级工厂便于测试替换，同时避免在导入阶段创建有运行时依赖的 service。
backup_config_service_factory: Callable[[], Any] = lambda: BackupConfigService
backup_storage_service_factory: Callable[[Mapping[str, Any]], Any] = (
    BackupStorageService
)
backup_job_service_factory: Callable[[], Any] = BackupJobService


def _safe_origin(url: str, *, origin_header: bool) -> tuple[str, str, int] | None:
    """解析可比较的 HTTP(S) origin；畸形输入返回 ``None``。"""
    value = str(url or "")
    if not value or value != value.strip() or any(ord(char) < 32 for char in value):
        return None
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except (TypeError, ValueError):
        return None
    scheme = parsed.scheme.lower()
    host = (parsed.hostname or "").lower()
    if (
        scheme not in {"http", "https"}
        or not host
        or parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
    ):
        return None
    if origin_header and (parsed.path not in {"", "/"} or parsed.query):
        return None
    effective_port = port if port is not None else (443 if scheme == "https" else 80)
    return scheme, host, effective_port


def _is_same_origin_request() -> bool:
    expected = _safe_origin(request.host_url, origin_header=False)
    if expected is None:
        return False
    source_header_present = False
    for header, is_origin in (("Origin", True), ("Referer", False)):
        if header not in request.headers:
            continue
        source_header_present = True
        supplied = _safe_origin(request.headers.get(header, ""), origin_header=is_origin)
        if supplied is None or supplied != expected:
            return False
    return source_header_present


def _backup_rate_limit_response(_request_limit: Any):
    """仅为本模块限流返回统一 API 错误信封。"""
    response, status_code = error_response(
        "请求过于频繁，请稍后重试", status_code=429
    )
    response.status_code = status_code
    return response


def backup_rate_limit(
    limit_value: str,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """应用模块级限流，并在全局 HTML 错误处理前返回安全 JSON。"""

    def decorate(view: Callable[..., Any]) -> Callable[..., Any]:
        limited_view = limiter.limit(
            limit_value, on_breach=_backup_rate_limit_response
        )(view)

        @wraps(view)
        def guarded(*args: Any, **kwargs: Any):
            try:
                return limited_view(*args, **kwargs)
            except RateLimitExceeded as exc:
                if exc.response is not None:
                    return exc.response
                return _backup_rate_limit_response(exc.limit)

        return guarded

    return decorate


def backup_write_guard(view: Callable[..., Any]) -> Callable[..., Any]:
    """仅保护本模块写接口的 XHR 与同源边界。"""

    @wraps(view)
    def guarded(*args: Any, **kwargs: Any):
        if request.headers.get("X-Requested-With") != "XMLHttpRequest":
            return error_response("请求被拒绝（缺少安全标头）", status_code=403)
        if not _is_same_origin_request():
            return error_response("请求来源校验失败", status_code=403)
        return view(*args, **kwargs)

    return guarded


def session_admin_required(view: Callable[..., Any]) -> Callable[..., Any]:
    """限制本模块只能使用完整管理员 Session，不接受仅 JWT 身份。"""

    @wraps(view)
    def guarded(*args: Any, **kwargs: Any):
        if not session.get("user_id"):
            return error_response("请使用管理员会话登录", status_code=401)
        if not session.get("is_admin"):
            return error_response("需要管理员权限", status_code=403)
        return view(*args, **kwargs)

    return guarded


def _log_safe_failure(event: str, exc: BaseException, *, job_id: str = "") -> None:
    """只记录安全结构化上下文，不记录异常文本或 traceback。"""
    request_id = str(getattr(g, "request_id", "") or "")
    if not _SAFE_REQUEST_ID_PATTERN.fullmatch(request_id):
        request_id = "redacted"
        g.request_id = request_id
    current_app.logger.error(
        "%s exception_type=%s request_id=%s job_id=%s",
        event,
        type(exc).__name__,
        request_id,
        job_id,
    )


def _config_service() -> Any:
    return backup_config_service_factory()


def _job_service() -> Any:
    return backup_job_service_factory()


def _job_to_dto(job: Any) -> dict[str, Any]:
    if hasattr(job, "to_dict"):
        dto = job.to_dict()
    elif isinstance(job, Mapping):
        dto = dict(job)
    else:
        raise TypeError("备份任务响应类型无效")
    if not isinstance(dto, Mapping):
        raise TypeError("备份任务响应类型无效")
    return dict(dto)


def _parse_limit() -> int:
    raw = request.args.get("limit", "100")
    if raw is None or not str(raw).isdigit():
        raise ValueError("limit 必须为 1 到 200 的整数")
    limit = int(raw)
    if not 1 <= limit <= 200:
        raise ValueError("limit 必须为 1 到 200 的整数")
    return limit


def _parse_job_id(job_id: str) -> str:
    try:
        return str(UUID(str(job_id)))
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError("备份任务不存在") from exc


@admin_api_bp.route("/settings/backup", methods=["GET"])
@session_admin_required
@admin_required
@backup_rate_limit("60 per minute")
def api_get_backup_config():
    try:
        return success_response(data=_config_service().get_config())
    except Exception as exc:
        _log_safe_failure("读取备份配置失败", exc)
        return error_response("读取备份配置失败，请稍后重试", status_code=500)


@admin_api_bp.route("/settings/backup", methods=["POST"])
@session_admin_required
@admin_required
@backup_write_guard
@backup_rate_limit("10 per minute")
def api_save_backup_config():
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict) or not data:
            return error_response("配置数据必须为非空对象", status_code=400)
        if set(data) - _CONFIG_FIELDS:
            return error_response("配置包含不支持的字段", status_code=400)
        saved = _config_service().save_config(
            dict(data), admin_id=session.get("user_id")
        )
        return success_response(data=saved, message="备份配置保存成功")
    except BackupConfigValidationError as exc:
        return error_response(str(exc), status_code=400)
    except BackupConfigError as exc:
        _log_safe_failure("保存备份配置时读取现有配置失败", exc)
        return error_response("备份配置不可用，请重新填写并保存", status_code=400)
    except Exception as exc:
        _log_safe_failure("保存备份配置失败", exc)
        return error_response("保存备份配置失败，请稍后重试", status_code=500)


@admin_api_bp.route("/settings/backup/test", methods=["POST"])
@session_admin_required
@admin_required
@backup_write_guard
@backup_rate_limit("5 per minute")
def api_test_backup_connection():
    try:
        runtime_config = _config_service().get_runtime_config()
        storage = backup_storage_service_factory(dict(runtime_config))
        storage.test_connection()
        return success_response(message="备份存储连接测试成功")
    except (BackupConfigError, BackupConfigValidationError):
        return error_response("备份配置不完整，请先保存完整配置", status_code=400)
    except Exception as exc:
        _log_safe_failure("备份存储连接测试失败", exc)
        return error_response("备份存储连接测试失败，请检查配置和网络", status_code=502)


@admin_api_bp.route("/backups", methods=["GET"])
@session_admin_required
@admin_required
@backup_rate_limit("60 per minute")
def api_list_backups():
    try:
        limit = _parse_limit()
        jobs = _job_service().list_jobs(limit=limit)
        return success_response(data={"items": jobs, "limit": limit})
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        _log_safe_failure("读取备份任务列表失败", exc)
        return error_response("读取备份任务列表失败，请稍后重试", status_code=500)


@admin_api_bp.route("/backups", methods=["POST"])
@session_admin_required
@admin_required
@backup_write_guard
@backup_rate_limit("3 per minute")
def api_create_backup():
    try:
        # 创建任务前强制读取并校验已保存的完整运行时配置。
        _config_service().get_runtime_config()
        job = _job_service().create_manual_job(created_by=session.get("user_id"))
        return success_response(data=_job_to_dto(job), message="备份任务已创建")
    except (BackupConfigError, BackupConfigValidationError):
        return error_response("备份配置不完整，请先保存完整配置", status_code=400)
    except BackupJobError:
        return error_response("当前备份任务状态冲突，请稍后重试", status_code=409)
    except Exception as exc:
        _log_safe_failure("创建备份任务失败", exc)
        return error_response("创建备份任务失败，请稍后重试", status_code=500)


@admin_api_bp.route("/backups/<string:job_id>/download", methods=["GET"])
@session_admin_required
@admin_required
@backup_rate_limit("10 per minute")
def api_download_backup(job_id: str):
    try:
        job_id_text = _parse_job_id(job_id)
    except ValueError:
        return error_response("备份任务不存在", status_code=404)

    try:
        url = _job_service().download_url(job_id_text)
        response = success_response(data={"url": str(url), "expires_in": 300})
        response.headers["Cache-Control"] = "no-store"
        return response
    except BackupJobNotFoundError:
        return error_response("备份任务不存在", status_code=404)
    except BackupJobConflictError:
        return error_response("备份任务当前不可下载", status_code=409)
    except Exception as exc:
        _log_safe_failure("生成备份下载链接失败", exc, job_id=job_id_text)
        return error_response("生成备份下载链接失败，请稍后重试", status_code=502)


@admin_api_bp.route("/backups/<string:job_id>", methods=["DELETE"])
@session_admin_required
@admin_required
@backup_write_guard
@backup_rate_limit("10 per minute")
def api_delete_backup(job_id: str):
    try:
        job_id_text = _parse_job_id(job_id)
    except ValueError:
        return error_response("备份任务不存在", status_code=404)

    try:
        _job_service().delete_completed_job(job_id_text)
        return success_response(message="备份删除成功")
    except BackupJobNotFoundError:
        return error_response("备份任务不存在", status_code=404)
    except BackupJobConflictError:
        return error_response("备份任务当前不可删除", status_code=409)
    except Exception as exc:
        _log_safe_failure("删除备份失败", exc, job_id=job_id_text)
        return error_response("删除备份失败，请稍后重试", status_code=502)
