# -*- coding: utf-8 -*-
"""Admin API routes - payment settings."""

from __future__ import annotations

from typing import Any, Dict

import requests
from flask import current_app, request, session

from app.core.extensions import limiter
from app.core.utils.api_response import error_response, success_response
from app.core.utils.decorators import admin_required
from app.modules.admin.services.system_config_service import SystemConfigService
from app.modules.payment.services.epay_service import (
    EPAY_CONFIG_KEYS,
    EPAY_DEFAULT_API_BASE_URL,
    EPAY_PAY_TYPES,
    EpayService,
)

from ..api_bp import admin_api_bp


_FIELD_DESCRIPTIONS: Dict[str, str] = {
    'epay_enabled': '是否启用易支付渠道',
    'epay_api_base_url': '易支付接口地址',
    'epay_pid': '易支付商户 ID',
    'epay_key': '易支付商户密钥',
    'epay_sitename': '易支付网站名称',
    'epay_notify_url': '易支付异步通知地址',
    'epay_return_url': '易支付同步跳转地址',
    'epay_default_type': '易支付默认支付方式',
    'epay_timeout': '易支付接口超时时间',
}


def _is_enabled(value: Any) -> bool:
    return value in [True, 'true', '1', 1, 'on', 'yes']


def _is_masked(value: Any) -> bool:
    return '*' in str(value or '')


def _normalize_payload(data: Dict[str, Any], persisted: Dict[str, Any]) -> Dict[str, str]:
    base_url = str(data.get('epay_api_base_url') or EPAY_DEFAULT_API_BASE_URL).strip().rstrip('/')
    default_type = str(data.get('epay_default_type') or 'alipay').strip().lower()
    if default_type not in EPAY_PAY_TYPES:
        raise ValueError('默认支付方式无效')

    try:
        timeout = int(data.get('epay_timeout') or 10)
    except (TypeError, ValueError):
        timeout = 10
    if timeout < 3 or timeout > 60:
        raise ValueError('接口超时时间必须在 3-60 秒之间')

    payload = {
        'epay_enabled': 'true' if _is_enabled(data.get('epay_enabled')) else 'false',
        'epay_api_base_url': base_url,
        'epay_pid': str(data.get('epay_pid') or '').strip(),
        'epay_key': str(data.get('epay_key') or ''),
        'epay_sitename': str(data.get('epay_sitename') or '').strip(),
        'epay_notify_url': str(data.get('epay_notify_url') or '').strip(),
        'epay_return_url': str(data.get('epay_return_url') or '').strip(),
        'epay_default_type': default_type,
        'epay_timeout': str(timeout),
    }

    if _is_masked(payload['epay_key']):
        payload['epay_key'] = str(persisted.get('key') or '')

    if not payload['epay_api_base_url'].startswith(('https://', 'http://')):
        raise ValueError('易支付接口地址必须以 http:// 或 https:// 开头')
    for key, label in (
        ('epay_notify_url', '异步通知地址'),
        ('epay_return_url', '同步跳转地址'),
    ):
        value = payload[key]
        if value and not value.startswith(('https://', 'http://')):
            raise ValueError(f'{label}必须以 http:// 或 https:// 开头')

    if _is_enabled(data.get('epay_enabled')):
        missing = []
        if not payload['epay_pid']:
            missing.append('商户 ID')
        if not payload['epay_key']:
            missing.append('商户密钥')
        if not payload['epay_sitename']:
            missing.append('网站名称')
        if missing:
            raise ValueError(f'启用易支付前请填写：{", ".join(missing)}')

    return payload


def _config_response_payload() -> Dict[str, Any]:
    cfg = EpayService.get_config(masked=True)
    return {
        'epay_enabled': cfg['enabled'],
        'epay_api_base_url': cfg['api_base_url'],
        'epay_pid': cfg['pid'],
        'epay_key': cfg['key'],
        'epay_sitename': cfg['sitename'],
        'epay_notify_url': cfg['notify_url'],
        'epay_return_url': cfg['return_url'],
        'epay_default_type': cfg['default_type'],
        'epay_timeout': cfg['timeout'],
    }


@admin_api_bp.route('/settings/payment/epay', methods=['GET'])
@admin_required
def api_get_epay_settings():
    return success_response(data=_config_response_payload())


@admin_api_bp.route('/settings/payment/epay', methods=['POST'])
@admin_required
def api_save_epay_settings():
    try:
        data = request.get_json(silent=True) or {}
        payload = _normalize_payload(data, EpayService.get_config())
        admin_id = session.get('user_id')

        for key in EPAY_CONFIG_KEYS:
            if key == 'epay_key' and not payload[key]:
                continue
            SystemConfigService.update_config(
                key,
                payload[key],
                _FIELD_DESCRIPTIONS.get(key, ''),
                admin_id,
            )

        return success_response(message='易支付配置保存成功（约 15 秒内生效）')
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except Exception as exc:
        current_app.logger.error('保存易支付配置失败: %s', exc, exc_info=True)
        return error_response(f'保存失败: {exc}', status_code=500)


@admin_api_bp.route('/settings/payment/epay/test', methods=['POST'])
@limiter.limit('5 per minute')
@admin_required
def api_test_epay_settings():
    try:
        data = request.get_json(silent=True) or {}
        payload = _normalize_payload(data, EpayService.get_config())
        config = {
            'api_base_url': payload['epay_api_base_url'],
            'pid': payload['epay_pid'],
            'key': payload['epay_key'],
            'timeout': int(payload['epay_timeout'] or 10),
        }
        result = EpayService.query_merchant(config)
        return success_response(
            data={
                'status_code': result.get('status_code'),
                'parsed': result.get('parsed'),
                'raw': result.get('raw'),
            },
            message='易支付商户信息查询成功',
        )
    except ValueError as exc:
        return error_response(str(exc), status_code=400)
    except requests.RequestException as exc:
        current_app.logger.warning('测试易支付配置失败: %s', exc, exc_info=True)
        return error_response('易支付接口请求失败，请检查接口地址、商户 ID、密钥和网络', status_code=502)
    except Exception as exc:
        current_app.logger.error('测试易支付配置失败: %s', exc, exc_info=True)
        return error_response(f'测试失败: {exc}', status_code=500)
