# -*- coding: utf-8 -*-
"""Admin API routes - sms settings."""

from typing import Any, Dict

from flask import current_app, jsonify, request, session

from app.core.extensions import limiter
from app.core.utils.decorators import admin_required
from app.core.utils.sms_service import send_sms_verify_code
from app.modules.admin.services.system_config_service import SystemConfigService

from ..api_bp import admin_api_bp

_SMS_FIELDS: Dict[str, str] = {
    'sms_access_key_id': '阿里云 AccessKey ID',
    'sms_access_key_secret': '阿里云 AccessKey Secret',
    'sms_sign_name': '短信签名',
    'sms_template_code': '登录/注册模板编码',
    'sms_template_code_bind': '绑定手机模板编码',
    'sms_template_code_reset': '重置密码模板编码',
    'sms_code_length': '验证码长度',
    'sms_valid_time': '验证码有效期（秒）',
    'sms_interval': '发送间隔（秒）',
    'sms_enabled': '是否启用短信服务',
    'sms_console_output': '是否控制台输出验证码',
}

_MASKED_FIELDS = {'sms_access_key_id', 'sms_access_key_secret'}
_BOOL_FIELDS = {'sms_enabled', 'sms_console_output'}
_INT_DEFAULTS = {
    'sms_code_length': 6,
    'sms_valid_time': 300,
    'sms_interval': 60,
}


def _normalize_value(key: str, value: Any) -> str:
    if key in _BOOL_FIELDS:
        return 'true' if value in [True, 'true', '1', 1, 'on', 'yes'] else 'false'

    if key in _INT_DEFAULTS:
        try:
            return str(int(value))
        except (TypeError, ValueError):
            return str(_INT_DEFAULTS[key])

    return str(value or '').strip()


def _masked_config_payload() -> Dict[str, Any]:
    cfg = SystemConfigService.get_sms_config_masked()
    return {
        'sms_access_key_id': cfg.get('access_key_id', ''),
        'sms_access_key_secret': cfg.get('access_key_secret', ''),
        'sms_sign_name': cfg.get('sign_name', ''),
        'sms_template_code': cfg.get('template_code', ''),
        'sms_template_code_bind': cfg.get('template_code_bind', ''),
        'sms_template_code_reset': cfg.get('template_code_reset', ''),
        'sms_code_length': cfg.get('code_length', 6),
        'sms_valid_time': cfg.get('valid_time', 300),
        'sms_interval': cfg.get('interval', 60),
        'sms_enabled': 'true' if cfg.get('enabled', True) else 'false',
        'sms_console_output': 'true' if cfg.get('console_output', False) else 'false',
    }


@admin_api_bp.route('/settings/sms', methods=['GET'])
@admin_required
def api_get_sms_config():
    return jsonify({'status': 'success', 'data': _masked_config_payload()})


@admin_api_bp.route('/settings/sms', methods=['POST'])
@admin_required
def api_save_sms_config():
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')

        for key, description in _SMS_FIELDS.items():
            value = data.get(key, '')

            if key in _MASKED_FIELDS and (not value or '****' in str(value)):
                continue

            normalized = _normalize_value(key, value)

            if key == 'sms_code_length':
                code_length = int(normalized or 6)
                if code_length < 4 or code_length > 8:
                    return jsonify({'status': 'error', 'message': '验证码长度必须在 4-8 位之间'}), 400

            if key in {'sms_valid_time', 'sms_interval'} and int(normalized or 0) <= 0:
                return jsonify({'status': 'error', 'message': '短信有效期和发送间隔必须大于 0'}), 400

            SystemConfigService.update_config(key, normalized, description, user_id)

        return jsonify({'status': 'success', 'message': '短信配置保存成功（约 15 秒内生效）'})
    except Exception as exc:
        current_app.logger.error('保存短信配置失败: %s', exc, exc_info=True)
        return jsonify({'status': 'error', 'message': f'保存失败: {exc}'}), 500


@admin_api_bp.route('/settings/sms/test', methods=['POST'])
@limiter.limit('5 per minute')
@admin_required
def api_test_sms_config():
    try:
        data = request.get_json() or {}
        phone = str(data.get('phone') or '').strip()
        if not phone:
            return jsonify({'status': 'error', 'message': '请填写测试手机号'}), 400

        persisted = SystemConfigService.get_sms_config()
        config = {
            'access_key_id': str(data.get('sms_access_key_id') or '').strip(),
            'access_key_secret': str(data.get('sms_access_key_secret') or ''),
            'sign_name': str(data.get('sms_sign_name') or '').strip(),
            'template_code': str(data.get('sms_template_code') or '').strip(),
            'code_length': int(data.get('sms_code_length') or 6),
            'valid_time': int(data.get('sms_valid_time') or 300),
            'interval': int(data.get('sms_interval') or 60),
            'console_output': data.get('sms_console_output', False) in [True, 'true', '1', 1],
        }

        for key, persisted_key in (
            ('access_key_id', 'access_key_id'),
            ('access_key_secret', 'access_key_secret'),
        ):
            if '****' in str(config[key]):
                config[key] = persisted.get(persisted_key, '')

        missing = []
        if not config['access_key_id']:
            missing.append('AccessKey ID')
        if not config['access_key_secret']:
            missing.append('AccessKey Secret')
        if not config['sign_name']:
            missing.append('短信签名')
        if not config['template_code']:
            missing.append('登录/注册模板编码')
        if missing:
            return jsonify({'status': 'error', 'message': f'配置不完整，请填写：{", ".join(missing)}'}), 400

        result = send_sms_verify_code(phone, config)
        if not result.success:
            message = result.error_message or result.error_code or '短信发送失败'
            return jsonify({'status': 'error', 'message': message}), 400

        message = f'测试短信已发送到 {phone}'
        if result.code:
            message += f'，控制台验证码：{result.code}'
        return jsonify({'status': 'success', 'message': message})
    except Exception as exc:
        current_app.logger.error('测试短信配置失败: %s', exc, exc_info=True)
        return jsonify({'status': 'error', 'message': f'测试失败: {exc}'}), 500
