# -*- coding: utf-8 -*-
"""Admin API routes - auth login method settings."""

from typing import Any, Dict

from flask import current_app, jsonify, request, session

from app.core.utils.decorators import admin_required
from app.modules.admin.services.system_config_service import SystemConfigService

from ..api_bp import admin_api_bp

_AUTH_LOGIN_FIELDS: Dict[str, str] = {
    'auth_phone_login_enabled': '是否启用手机号验证码登录/注册',
    'auth_wechat_login_enabled': '是否启用微信登录/扫码登录',
}


def _normalize_bool(value: Any) -> str:
    return 'true' if value in [True, 'true', '1', 1, 'on', 'yes'] else 'false'


@admin_api_bp.route('/settings/auth-login', methods=['GET'])
@admin_required
def api_get_auth_login_config():
    return jsonify({
        'status': 'success',
        'data': SystemConfigService.get_auth_login_methods_form_config(),
    })


@admin_api_bp.route('/settings/auth-login', methods=['POST'])
@admin_required
def api_save_auth_login_config():
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')

        for key, description in _AUTH_LOGIN_FIELDS.items():
            SystemConfigService.update_config(
                key,
                _normalize_bool(data.get(key, True)),
                description,
                user_id,
            )

        return jsonify({'status': 'success', 'message': '登录方式配置保存成功（约 15 秒内生效）'})
    except Exception as exc:
        current_app.logger.error('保存登录方式配置失败: %s', exc, exc_info=True)
        return jsonify({'status': 'error', 'message': '保存失败，请稍后重试'}), 500
