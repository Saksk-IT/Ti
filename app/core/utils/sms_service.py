# -*- coding: utf-8 -*-
"""
阿里云号码认证服务（DYPNS）封装

使用 SendSmsVerifyCode / CheckSmsVerifyCode 接口，
验证码由阿里云托管生成和校验，本地无需存储验证码。
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SendSmsResult:
    """发送短信验证码结果"""
    success: bool
    request_id: str = ''
    biz_id: str = ''
    code: str = ''          # 仅 ReturnVerifyCode=true 时返回
    error_code: str = ''
    error_message: str = ''


@dataclass(frozen=True)
class CheckSmsResult:
    """校验短信验证码结果"""
    success: bool
    request_id: str = ''
    verify_result: str = ''  # PASS / UNKNOWN
    error_code: str = ''
    error_message: str = ''


def _build_client(config: Dict[str, Any]):
    """构建阿里云 DYPNS Client（每次新建，避免多线程状态共享）"""
    from alibabacloud_dypnsapi20170525.client import Client
    from alibabacloud_tea_openapi.models import Config as OpenApiConfig

    ak_id = config.get('access_key_id') or ''
    ak_secret = config.get('access_key_secret') or ''
    if not ak_id or not ak_secret:
        raise ValueError('阿里云 AccessKey 未配置')

    api_config = OpenApiConfig(
        access_key_id=ak_id,
        access_key_secret=ak_secret,
        endpoint='dypnsapi.aliyuncs.com',
    )
    return Client(api_config)


def send_sms_verify_code(phone: str, config: Dict[str, Any]) -> SendSmsResult:
    """发送短信验证码（阿里云托管生成验证码）。

    Parameters
    ----------
    phone : str
        手机号
    config : dict
        必须包含 access_key_id, access_key_secret, sign_name, template_code
        可选 code_length(默认6), valid_time(默认300), console_output(默认False)
    """
    from alibabacloud_dypnsapi20170525.models import (
        SendSmsVerifyCodeRequest,
    )

    console_output = config.get('console_output', False)
    code_length = int(config.get('code_length', 6) or 6)
    valid_time = int(config.get('valid_time', 300) or 300)

    try:
        client = _build_client(config)
        req = SendSmsVerifyCodeRequest(
            phone_number=phone,
            sign_name=config.get('sign_name', ''),
            template_code=config.get('template_code', ''),
            template_param='{"code":"##code##"}',
            code_length=code_length,
            valid_time=valid_time,
            interval=int(config.get('interval', 60) or 60),
            return_verify_code=console_output,
        )
        resp = client.send_sms_verify_code(req)
        body = resp.body

        if body.code != 'OK':
            return SendSmsResult(
                success=False,
                request_id=body.request_id or '',
                error_code=body.code or '',
                error_message=body.message or '',
            )

        model = body.model
        biz_id = (model.biz_id if model else '') or ''
        verify_code = (model.verify_code if model else '') or ''

        if console_output and verify_code:
            logger.info(
                '\n========== 短信验证码(控制台) ==========\n'
                '  手机号: %s\n  验证码: %s\n'
                '========================================',
                phone, verify_code,
            )

        return SendSmsResult(
            success=True,
            request_id=body.request_id or '',
            biz_id=biz_id,
            code=verify_code,
        )
    except ValueError:
        raise
    except Exception as exc:
        logger.error('短信发送异常: phone=%s, error=%s', phone, exc, exc_info=True)
        return SendSmsResult(
            success=False,
            error_code='SDK_EXCEPTION',
            error_message=str(exc),
        )


def check_sms_verify_code(phone: str, code: str, config: Dict[str, Any]) -> CheckSmsResult:
    """校验短信验证码（阿里云服务端校验）。

    Parameters
    ----------
    phone : str
        手机号
    code : str
        用户输入的验证码
    config : dict
        必须包含 access_key_id, access_key_secret
    """
    from alibabacloud_dypnsapi20170525.models import (
        CheckSmsVerifyCodeRequest,
    )

    try:
        client = _build_client(config)
        req = CheckSmsVerifyCodeRequest(
            phone_number=phone,
            verify_code=code,
        )
        resp = client.check_sms_verify_code(req)
        body = resp.body

        if body.code != 'OK':
            return CheckSmsResult(
                success=False,
                request_id=body.request_id or '',
                error_code=body.code or '',
                error_message=body.message or '',
            )

        model = body.model
        verify_result = (model.verify_result if model else '') or ''

        return CheckSmsResult(
            success=(verify_result == 'PASS'),
            request_id=body.request_id or '',
            verify_result=verify_result,
        )
    except ValueError:
        raise
    except Exception as exc:
        logger.error('短信校验异常: phone=%s, error=%s', phone, exc, exc_info=True)
        return CheckSmsResult(
            success=False,
            error_code='SDK_EXCEPTION',
            error_message=str(exc),
        )
