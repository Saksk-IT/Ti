# -*- coding: utf-8 -*-
"""易支付渠道服务。

当前只封装配置读取、MD5 签名、支付跳转 URL 生成和商户/订单查询能力。
具体业务订单创建与回调落库由后续业务支付流程接入。
"""

from __future__ import annotations

import hashlib
import json
import os
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Mapping
from urllib.parse import urlencode

import requests

from app.modules.admin.services.system_config_service import SystemConfigService


EPAY_DEFAULT_API_BASE_URL = 'https://z-pay.cn'
EPAY_PAY_TYPES = {'alipay', 'wxpay', 'qqpay', 'tenpay'}
EPAY_CONFIG_KEYS = (
    'epay_enabled',
    'epay_api_base_url',
    'epay_pid',
    'epay_key',
    'epay_sitename',
    'epay_notify_url',
    'epay_return_url',
    'epay_default_type',
    'epay_timeout',
)


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


def _as_int(value: Any, default: int, *, min_value: int, max_value: int) -> int:
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = int(default)
    return max(min_value, min(max_value, result))


def _clean_base_url(value: str) -> str:
    text = (value or EPAY_DEFAULT_API_BASE_URL).strip().rstrip('/')
    return text or EPAY_DEFAULT_API_BASE_URL


def _config_value(config_key: str, env_key: str, default: Any = '') -> Any:
    row = SystemConfigService.get_config(config_key)
    if row and row.get('config_value') not in (None, ''):
        return row['config_value']
    return os.environ.get(env_key, default)


def _parse_response_text(text: str) -> Any:
    body = (text or '').strip()
    if not body:
        return ''
    try:
        return json.loads(body)
    except ValueError:
        return body


class EpayService:
    """易支付渠道服务。"""

    PAY_TYPES = EPAY_PAY_TYPES

    @staticmethod
    def get_config(*, masked: bool = False) -> Dict[str, Any]:
        key = str(_config_value('epay_key', 'EPAY_KEY', '') or '')
        return {
            'enabled': _as_bool(_config_value('epay_enabled', 'EPAY_ENABLED', False), False),
            'api_base_url': _clean_base_url(str(_config_value('epay_api_base_url', 'EPAY_API_BASE_URL', EPAY_DEFAULT_API_BASE_URL) or '')),
            'pid': str(_config_value('epay_pid', 'EPAY_PID', '') or '').strip(),
            'key': SystemConfigService.mask_secret(key, prefix=3, suffix=3) if masked else key,
            'sitename': str(_config_value('epay_sitename', 'EPAY_SITENAME', '') or '').strip(),
            'notify_url': str(_config_value('epay_notify_url', 'EPAY_NOTIFY_URL', '') or '').strip(),
            'return_url': str(_config_value('epay_return_url', 'EPAY_RETURN_URL', '') or '').strip(),
            'default_type': EpayService.normalize_pay_type(
                str(_config_value('epay_default_type', 'EPAY_DEFAULT_TYPE', 'alipay') or 'alipay')
            ),
            'timeout': _as_int(_config_value('epay_timeout', 'EPAY_TIMEOUT', 10), 10, min_value=3, max_value=60),
        }

    @staticmethod
    def normalize_pay_type(value: str) -> str:
        normalized = (value or '').strip().lower()
        if normalized not in EPAY_PAY_TYPES:
            return 'alipay'
        return normalized

    @staticmethod
    def build_sign(params: Mapping[str, Any], key: str) -> tuple[str, str]:
        ordered_keys = sorted(k for k, value in params.items() if value not in (None, '') and k not in {'sign', 'sign_type'})
        sign_base = '&'.join(f'{name}={params[name]}' for name in ordered_keys)
        sign = hashlib.md5((sign_base + str(key or '')).encode('utf-8')).hexdigest()
        return sign_base, sign

    @staticmethod
    def build_payment_request(
        *,
        money: Any,
        name: str,
        out_trade_no: str,
        pay_type: str | None = None,
        notify_url: str | None = None,
        return_url: str | None = None,
        config: Mapping[str, Any] | None = None,
    ) -> Dict[str, Any]:
        cfg = dict(config or EpayService.get_config())
        EpayService.validate_required_config(cfg)

        amount = EpayService.normalize_money(money)
        params = {
            'money': amount,
            'name': str(name or '').strip(),
            'notify_url': str(notify_url or cfg.get('notify_url') or '').strip(),
            'out_trade_no': str(out_trade_no or '').strip(),
            'pid': str(cfg.get('pid') or '').strip(),
            'return_url': str(return_url or cfg.get('return_url') or '').strip(),
            'sitename': str(cfg.get('sitename') or '').strip(),
            'type': EpayService.normalize_pay_type(str(pay_type or cfg.get('default_type') or 'alipay')),
        }
        missing = [label for key, label in {
            'name': '商品名称',
            'notify_url': '异步通知地址',
            'out_trade_no': '商户订单号',
            'return_url': '同步跳转地址',
            'sitename': '网站名称',
        }.items() if not params.get(key)]
        if missing:
            raise ValueError(f'易支付下单参数不完整：{", ".join(missing)}')

        sign_base, sign = EpayService.build_sign(params, str(cfg.get('key') or ''))
        signed_params = {**params, 'sign': sign, 'sign_type': 'MD5'}
        url = f"{_clean_base_url(str(cfg.get('api_base_url') or ''))}/submit.php?{urlencode(signed_params)}"
        return {
            'url': url,
            'params': signed_params,
            'sign_base': sign_base,
        }

    @staticmethod
    def normalize_money(value: Any) -> str:
        try:
            amount = Decimal(str(value)).quantize(Decimal('0.01'))
        except (InvalidOperation, ValueError):
            raise ValueError('支付金额格式无效')
        if amount <= 0:
            raise ValueError('支付金额必须大于 0')
        return format(amount, 'f')

    @staticmethod
    def validate_required_config(config: Mapping[str, Any] | None = None) -> None:
        cfg = dict(config or EpayService.get_config())
        missing = []
        if not str(cfg.get('api_base_url') or '').strip():
            missing.append('接口地址')
        if not str(cfg.get('pid') or '').strip():
            missing.append('商户 ID')
        if not str(cfg.get('key') or '').strip():
            missing.append('商户密钥')
        if missing:
            raise ValueError(f'易支付配置不完整：{", ".join(missing)}')

    @staticmethod
    def query_merchant(config: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        cfg = dict(config or EpayService.get_config())
        EpayService.validate_required_config(cfg)
        return EpayService._api_get('query', cfg)

    @staticmethod
    def query_order(out_trade_no: str, config: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        trade_no = str(out_trade_no or '').strip()
        if not trade_no:
            raise ValueError('商户订单号不能为空')
        cfg = dict(config or EpayService.get_config())
        EpayService.validate_required_config(cfg)
        return EpayService._api_get('order', cfg, {'out_trade_no': trade_no})

    @staticmethod
    def _api_get(act: str, config: Mapping[str, Any], extra: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        params = {
            'act': act,
            'pid': str(config.get('pid') or '').strip(),
            'key': str(config.get('key') or ''),
        }
        if extra:
            params = {**params, **dict(extra)}

        resp = requests.get(
            f"{_clean_base_url(str(config.get('api_base_url') or ''))}/api.php",
            params=params,
            timeout=_as_int(config.get('timeout'), 10, min_value=3, max_value=60),
        )
        resp.raise_for_status()
        return {
            'status_code': resp.status_code,
            'raw': resp.text,
            'parsed': _parse_response_text(resp.text),
        }
