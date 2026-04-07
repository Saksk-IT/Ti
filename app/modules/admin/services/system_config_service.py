# -*- coding: utf-8 -*-
"""
系统配置管理服务
"""
import os
import threading
import time
from typing import Dict, Any, List, Optional

from app.core.extensions import db
from app.models.system import SystemConfig


_CACHE_TTL_SECONDS = int(os.environ.get('SYSTEM_CONFIG_CACHE_TTL_SECONDS', '15') or 15)
_CACHE_LOCK = threading.Lock()
_CACHE: Dict[str, Any] = {}
_MISSING = object()


def _now() -> float:
    return time.monotonic()


def _cache_get(key: str):
    ttl = _CACHE_TTL_SECONDS
    if ttl <= 0:
        return _MISSING

    with _CACHE_LOCK:
        item = _CACHE.get(key)
        if not item:
            return _MISSING
        exp_at, value = item
        if exp_at < _now():
            _CACHE.pop(key, None)
            return _MISSING
        return value


def _cache_set(key: str, value: Any):
    ttl = _CACHE_TTL_SECONDS
    if ttl <= 0:
        return
    with _CACHE_LOCK:
        _CACHE[key] = (_now() + float(ttl), value)


def _cache_clear():
    with _CACHE_LOCK:
        _CACHE.clear()


def _as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return bool(default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if not text:
        return bool(default)
    return text in {'1', 'true', 'yes', 'on'}


def _as_int(value: Any, default: int) -> int:
    if value is None or str(value).strip() == '':
        return int(default)
    try:
        return int(value)
    except Exception:
        return int(default)


class SystemConfigService:
    """系统配置管理服务类"""
    
    @staticmethod
    def get_all_configs() -> List[Dict[str, Any]]:
        """获取所有系统配置"""
        cached = _cache_get('__all__')
        if cached is not _MISSING and isinstance(cached, list):
            return [dict(x) for x in cached]

        rows = SystemConfig.query.order_by(SystemConfig.config_key).all()
        result = [
            {
                'id': r.id,
                'config_key': r.config_key,
                'config_value': r.config_value,
                'description': r.description,
                'updated_at': r.updated_at,
                'updated_by': r.updated_by,
            }
            for r in rows
        ]
        _cache_set('__all__', result)
        return result

    @staticmethod
    def get_config(config_key: str) -> Optional[Dict[str, Any]]:
        """获取指定配置"""
        ck = f'key:{config_key}'
        cached = _cache_get(ck)
        if cached is not _MISSING:
            return dict(cached) if isinstance(cached, dict) else None

        row = SystemConfig.query.filter_by(config_key=config_key).first()
        if not row:
            _cache_set(ck, None)
            return None

        result = {
            'id': row.id,
            'config_key': row.config_key,
            'config_value': row.config_value,
            'description': row.description,
            'updated_at': row.updated_at,
            'updated_by': row.updated_by,
        }
        _cache_set(ck, result)
        return result

    @staticmethod
    def update_config(
        config_key: str,
        config_value: str,
        description: Optional[str] = None,
        admin_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """更新系统配置"""
        existing = SystemConfig.query.filter_by(config_key=config_key).first()

        if existing:
            existing.config_value = config_value
            if description:
                existing.description = description
            existing.updated_by = admin_id
        else:
            existing = SystemConfig(
                config_key=config_key,
                config_value=config_value,
                description=description or '',
                updated_by=admin_id,
            )
            db.session.add(existing)

        db.session.commit()
        _cache_clear()

        return SystemConfigService.get_config(config_key)
    
    @staticmethod
    def get_quiz_limit_config() -> Dict[str, Any]:
        """
        获取刷题限制相关配置
        
        Returns:
            包含功能开关和限制数量的字典
        """
        enabled_config = SystemConfigService.get_config('quiz_limit_enabled')
        count_config = SystemConfigService.get_config('quiz_limit_count')
        
        return {
            'quiz_limit_enabled': enabled_config['config_value'] == '1' if enabled_config else False,
            'quiz_limit_count': int(count_config['config_value']) if count_config else 100
        }
    
    @staticmethod
    def get_email_bind_required_config() -> bool:
        """
        获取邮箱绑定是否必需的配置

        Returns:
            如果邮箱绑定必需返回True，否则返回False（默认True，保持向后兼容）
        """
        config = SystemConfigService.get_config('email_bind_required')
        if config:
            return config['config_value'] == '1'
        # 默认返回True，保持向后兼容（原有行为）
        return True

    @staticmethod
    def _get_runtime_value(config_key: str, app_key: str, default: Any = '') -> Any:
        row = SystemConfigService.get_config(config_key)
        if row and row.get('config_value') not in (None, ''):
            return row['config_value']

        try:
            from flask import current_app

            return current_app.config.get(app_key, default)
        except RuntimeError:
            return os.environ.get(app_key, default)

    @staticmethod
    def mask_secret(value: str, prefix: int = 3, suffix: int = 3) -> str:
        text = (value or '').strip()
        if not text:
            return ''
        if len(text) <= (prefix + suffix):
            return '***'
        return f'{text[:prefix]}****{text[-suffix:]}'

    # ── DashScope AI 配置 ──────────────────────────────────

    _DASHSCOPE_KEYS = (
        'dashscope_api_key',
        'dashscope_base_url',
        'dashscope_model',
        'dashscope_timeout',
    )

    @staticmethod
    def mask_api_key(key: str) -> str:
        """API Key 脱敏：保留前 3 位 + 后 3 位，中间用 **** 替代"""
        return SystemConfigService.mask_secret(key, prefix=3, suffix=3)

    @staticmethod
    def get_dashscope_config() -> Dict[str, Any]:
        """获取 DashScope 配置，DB 优先、.env fallback。

        Returns:
            {api_key, base_url, model, timeout} — 均为实际可用值
        """
        return {
            'api_key': str(SystemConfigService._get_runtime_value('dashscope_api_key', 'DASHSCOPE_API_KEY', '') or '').strip(),
            'base_url': str(SystemConfigService._get_runtime_value(
                'dashscope_base_url',
                'DASHSCOPE_BASE_URL',
                'https://dashscope.aliyuncs.com/compatible-mode/v1',
            ) or 'https://dashscope.aliyuncs.com/compatible-mode/v1').strip(),
            'model': str(SystemConfigService._get_runtime_value('dashscope_model', 'DASHSCOPE_MODEL', 'qwen-plus') or 'qwen-plus').strip() or 'qwen-plus',
            'timeout': _as_int(SystemConfigService._get_runtime_value('dashscope_timeout', 'DASHSCOPE_TIMEOUT', 25), 25),
        }

    @staticmethod
    def get_dashscope_config_masked() -> Dict[str, Any]:
        """同 get_dashscope_config，但 api_key 脱敏（用于前端展示）"""
        cfg = SystemConfigService.get_dashscope_config()
        return {
            **cfg,
            'api_key': SystemConfigService.mask_api_key(cfg['api_key']),
        }

    # ── Mail 配置 ─────────────────────────────────────────

    @staticmethod
    def get_mail_config() -> Dict[str, Any]:
        return {
            'server': str(SystemConfigService._get_runtime_value('mail_server', 'MAIL_SERVER', '') or '').strip(),
            'port': _as_int(SystemConfigService._get_runtime_value('mail_port', 'MAIL_PORT', 587), 587),
            'use_tls': _as_bool(SystemConfigService._get_runtime_value('mail_use_tls', 'MAIL_USE_TLS', True), True),
            'use_ssl': _as_bool(SystemConfigService._get_runtime_value('mail_use_ssl', 'MAIL_USE_SSL', False), False),
            'username': str(SystemConfigService._get_runtime_value('mail_username', 'MAIL_USERNAME', '') or '').strip(),
            'password': str(SystemConfigService._get_runtime_value('mail_password', 'MAIL_PASSWORD', '') or ''),
            'sender': str(SystemConfigService._get_runtime_value('mail_default_sender', 'MAIL_DEFAULT_SENDER', '') or '').strip(),
            'sender_name': str(SystemConfigService._get_runtime_value('mail_default_sender_name', 'MAIL_DEFAULT_SENDER_NAME', '系统通知') or '系统通知').strip() or '系统通知',
            'enabled': _as_bool(SystemConfigService._get_runtime_value('mail_enabled', 'MAIL_ENABLED', True), True),
            'console_output': _as_bool(SystemConfigService._get_runtime_value('mail_console_output', 'MAIL_CONSOLE_OUTPUT', False), False),
        }

    @staticmethod
    def get_mail_config_masked() -> Dict[str, Any]:
        cfg = SystemConfigService.get_mail_config()
        return {
            **cfg,
            'password': '***' if cfg.get('password') else '',
        }

    # ── SMS 配置 ──────────────────────────────────────────

    @staticmethod
    def get_sms_config() -> Dict[str, Any]:
        return {
            'access_key_id': str(SystemConfigService._get_runtime_value('sms_access_key_id', 'ALIYUN_ACCESS_KEY_ID', '') or '').strip(),
            'access_key_secret': str(SystemConfigService._get_runtime_value('sms_access_key_secret', 'ALIYUN_ACCESS_KEY_SECRET', '') or ''),
            'sign_name': str(SystemConfigService._get_runtime_value('sms_sign_name', 'ALIYUN_SMS_SIGN_NAME', '') or '').strip(),
            'template_code': str(SystemConfigService._get_runtime_value('sms_template_code', 'ALIYUN_SMS_TEMPLATE_CODE', '') or '').strip(),
            'template_code_bind': str(SystemConfigService._get_runtime_value('sms_template_code_bind', 'ALIYUN_SMS_TEMPLATE_CODE_BIND', '') or '').strip(),
            'template_code_reset': str(SystemConfigService._get_runtime_value('sms_template_code_reset', 'ALIYUN_SMS_TEMPLATE_CODE_RESET', '') or '').strip(),
            'code_length': _as_int(SystemConfigService._get_runtime_value('sms_code_length', 'ALIYUN_SMS_CODE_LENGTH', 6), 6),
            'valid_time': _as_int(SystemConfigService._get_runtime_value('sms_valid_time', 'ALIYUN_SMS_VALID_TIME', 300), 300),
            'interval': _as_int(SystemConfigService._get_runtime_value('sms_interval', 'ALIYUN_SMS_INTERVAL', 60), 60),
            'enabled': _as_bool(SystemConfigService._get_runtime_value('sms_enabled', 'SMS_ENABLED', True), True),
            'console_output': _as_bool(SystemConfigService._get_runtime_value('sms_console_output', 'SMS_CONSOLE_OUTPUT', False), False),
        }

    @staticmethod
    def get_sms_config_masked() -> Dict[str, Any]:
        cfg = SystemConfigService.get_sms_config()
        return {
            **cfg,
            'access_key_id': SystemConfigService.mask_secret(cfg['access_key_id'], prefix=3, suffix=3),
            'access_key_secret': SystemConfigService.mask_secret(cfg['access_key_secret'], prefix=3, suffix=3),
        }



