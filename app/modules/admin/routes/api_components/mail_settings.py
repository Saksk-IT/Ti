# -*- coding: utf-8 -*-
"""Admin API routes - mail settings (SQLAlchemy ORM)."""

import secrets
import string
import logging
from typing import Dict, Any

from flask import current_app, jsonify, request, session

from app.core.extensions import db, limiter
from app.models.system import SystemConfig
from app.core.utils.decorators import admin_required

from ..api_bp import admin_api_bp

logger = logging.getLogger(__name__)

# 邮件配置字段定义
_MAIL_FIELDS: Dict[str, str] = {
    'mail_server': 'SMTP服务器地址',
    'mail_port': 'SMTP端口',
    'mail_use_tls': '是否使用TLS',
    'mail_use_ssl': '是否使用SSL',
    'mail_username': '邮箱用户名',
    'mail_password': '邮箱授权码',
    'mail_default_sender': '默认发件人',
    'mail_default_sender_name': '默认发件人名称',
    'mail_enabled': '是否启用邮件服务',
    'mail_console_output': '是否控制台输出（开发模式）',
}

_BOOL_FIELDS = {'mail_use_tls', 'mail_use_ssl', 'mail_enabled', 'mail_console_output'}


@admin_api_bp.route('/settings/mail', methods=['GET'])
@admin_required
def api_get_mail_config():
    """获取邮件配置"""
    rows = SystemConfig.query.filter(
        SystemConfig.config_key.like('mail_%')
    ).order_by(SystemConfig.config_key).all()

    mail_config = {}
    for row in rows:
        key = row.config_key
        value = row.config_value
        # 对于密码字段，不返回实际值
        if 'password' in key.lower():
            mail_config[key] = '***' if value else ''
        else:
            mail_config[key] = value

    return jsonify({'status': 'success', 'data': mail_config})


def _normalize_value(key: str, value: Any) -> str:
    """统一转换配置值为字符串"""
    if key in _BOOL_FIELDS:
        return 'true' if value in [True, 'true', '1', 1] else 'false'
    if key == 'mail_port':
        try:
            return str(int(value))
        except (ValueError, TypeError):
            return '587'
    return str(value) if value is not None else ''


def _upsert_config(key: str, value: str, description: str, user_id: int) -> None:
    """插入或更新单条配置（ORM）"""
    row = SystemConfig.query.filter_by(config_key=key).first()
    if row:
        row.config_value = value
        row.description = description
        row.updated_by = user_id
    else:
        db.session.add(SystemConfig(
            config_key=key,
            config_value=value,
            description=description,
            updated_by=user_id,
        ))


@admin_api_bp.route('/settings/mail', methods=['POST'])
@admin_required
def api_save_mail_config():
    """保存邮件配置"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        for key, description in _MAIL_FIELDS.items():
            value = data.get(key, '')

            # 密码字段：***或空 → 跳过（保持原值）
            if 'password' in key.lower() and value in ('***', ''):
                continue

            # 验证授权码长度
            if key == 'mail_password' and value and len(value) < 6:
                return jsonify({
                    'status': 'error',
                    'message': '邮箱授权码长度至少需要6位，请检查是否正确输入'
                }), 400

            value = _normalize_value(key, value)
            _upsert_config(key, value, description, user_id)

        db.session.commit()
        return jsonify({'status': 'success', 'message': '邮件配置保存成功'})
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'保存邮件配置失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'保存失败: {e}'}), 500


@admin_api_bp.route('/settings/mail/test', methods=['POST'])
@limiter.limit("5 per minute")
@admin_required
def api_test_mail_config():
    """测试邮件配置（不写库，直接用传入参数测试）"""
    try:
        data = request.get_json()
        test_email = data.get('email')
        if not test_email:
            return jsonify({'status': 'error', 'message': '请提供测试邮箱地址'}), 400

        # 从请求中构建临时 SMTP 配置
        smtp_config = {
            'server': data.get('mail_server', ''),
            'port': int(data.get('mail_port', 587) or 587),
            'use_tls': data.get('mail_use_tls', True) in [True, 'true', '1', 1],
            'use_ssl': data.get('mail_use_ssl', False) in [True, 'true', '1', 1],
            'username': data.get('mail_username', ''),
            'password': data.get('mail_password', ''),
            'sender': data.get('mail_default_sender', ''),
            'sender_name': data.get('mail_default_sender_name', '系统通知'),
        }

        # 密码为 *** 时从数据库读取已保存的值
        if smtp_config['password'] == '***':
            row = SystemConfig.query.filter_by(config_key='mail_password').first()
            smtp_config['password'] = row.config_value if row else ''

        # 验证必填字段
        missing = []
        if not smtp_config['server']:
            missing.append('SMTP服务器地址')
        if not smtp_config['username']:
            missing.append('邮箱用户名')
        if not smtp_config['password']:
            missing.append('邮箱授权码')
        if not smtp_config['sender']:
            missing.append('默认发件人')
        if missing:
            return jsonify({
                'status': 'error',
                'message': f'配置不完整，请填写：{", ".join(missing)}'
            }), 400

        # 直接用临时配置发送测试邮件，不经过数据库
        from app.core.utils.email_service import EmailService
        code = EmailService.generate_verification_code()
        subject, body_html = EmailService._render_email_template(
            'bind_code', email=test_email, code=code
        )
        success = EmailService._send_email_smtp_with_config(
            to_email=test_email, subject=subject,
            body_html=body_html, config=smtp_config
        )

        if success:
            return jsonify({
                'status': 'success',
                'message': f'测试邮件已发送到 {test_email}，验证码：{code}'
            })

        return jsonify({
            'status': 'error',
            'message': '邮件发送失败，请检查SMTP配置是否正确（服务器地址、端口、用户名、授权码）'
        }), 400
    except Exception as e:
        current_app.logger.error(f'测试邮件配置失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'测试失败: {e}'}), 500


@admin_api_bp.route('/settings/mail/template-preview', methods=['POST'])
@admin_required
def api_get_mail_template_preview():
    """获取邮件模板预览"""
    try:
        data = request.get_json()
        template_type = data.get('template_type', 'bind_code')

        valid_types = ['bind_code', 'login_code', 'reset_password']
        if template_type not in valid_types:
            return jsonify({
                'status': 'error',
                'message': f'无效的模板类型，支持的类型: {", ".join(valid_types)}'
            }), 400

        digits = string.digits
        sample_code = ''.join(secrets.choice(digits) for _ in range(6))
        sample_email = data.get('email', 'user@example.com')

        from app.core.utils.email_templates import render_template
        html_content = render_template(
            template_type, email=sample_email, code=sample_code
        )

        return jsonify({
            'status': 'success',
            'html': html_content,
            'template_type': template_type,
        })
    except Exception as e:
        current_app.logger.error(f'获取邮件模板预览失败: {e}', exc_info=True)
        return jsonify({'status': 'error', 'message': f'获取预览失败: {e}'}), 500

