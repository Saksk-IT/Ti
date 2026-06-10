# -*- coding: utf-8 -*-
"""Admin API routes - WeChat mini program settings."""

import re
from typing import Any, Dict

from flask import current_app, jsonify, request, session

from app.core.utils.decorators import admin_required
from app.modules.admin.services.system_config_service import SystemConfigService

from ..api_bp import admin_api_bp

_APPID_RE = re.compile(r'^wx[a-zA-Z0-9]{8,}$')

_WECHAT_FIELDS: Dict[str, str] = {
    'wechat_appid': '微信小程序 AppID',
    'wechat_secret': '微信小程序 AppSecret',
    'wechat_minicode_env_version': '扫码登录小程序码版本',
    'wechat_minicode_check_path': '扫码登录小程序码路径校验',
}


def _normalize_check_path(value: Any) -> str:
    if isinstance(value, str):
        value = value.strip().lower()
    if value in [True, 'true', '1', 1, 'on', 'yes']:
        return 'true'
    if value in [False, 'false', '0', 0, 'off', 'no']:
        return 'false'
    return 'auto'


def _normalize_env_version(value: Any) -> str:
    text = str(value or '').strip().lower()
    return text if text in {'release', 'trial', 'develop'} else ''


def _masked_config_payload() -> Dict[str, str]:
    return SystemConfigService.get_wechat_miniprogram_form_config()


@admin_api_bp.route('/settings/wechat-miniprogram', methods=['GET'])
@admin_required
def api_get_wechat_miniprogram_config():
    return jsonify({'status': 'success', 'data': _masked_config_payload()})


@admin_api_bp.route('/settings/wechat-miniprogram', methods=['POST'])
@admin_required
def api_save_wechat_miniprogram_config():
    try:
        data = request.get_json() or {}
        user_id = session.get('user_id')

        appid = str(data.get('wechat_appid') or '').strip()
        secret = str(data.get('wechat_secret') or '').strip()
        env_version = _normalize_env_version(data.get('wechat_minicode_env_version'))
        check_path = _normalize_check_path(data.get('wechat_minicode_check_path'))

        if appid and not _APPID_RE.fullmatch(appid):
            return jsonify({'status': 'error', 'message': 'AppID 格式不正确，应以 wx 开头'}), 400

        if secret and not SystemConfigService.is_masked_secret(secret) and len(secret) < 16:
            return jsonify({'status': 'error', 'message': 'AppSecret 长度不正确，请检查是否填写完整'}), 400

        normalized = {
            'wechat_appid': appid,
            'wechat_secret': secret,
            'wechat_minicode_env_version': env_version,
            'wechat_minicode_check_path': check_path,
        }

        for key, description in _WECHAT_FIELDS.items():
            value = normalized[key]
            if key == 'wechat_secret' and (not value or SystemConfigService.is_masked_secret(value)):
                continue
            SystemConfigService.update_config(key, value, description, user_id)

        return jsonify({'status': 'success', 'message': '微信小程序配置保存成功（约 15 秒内生效）'})
    except Exception as exc:
        current_app.logger.error('保存微信小程序配置失败: %s', exc, exc_info=True)
        return jsonify({'status': 'error', 'message': '保存失败，请稍后重试'}), 500
