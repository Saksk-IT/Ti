# -*- coding: utf-8 -*-
"""Admin API routes - mail settings."""

import datetime
import io
import json
import os
import sqlite3
import zipfile

import pandas as pd
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

from app.core.extensions import limiter
from app.core.utils.database import get_db
from app.core.utils.fill_blank_parser import parse_fill_blank
from app.core.utils.validators import parse_int, validate_password

from ..api_bp import admin_api_bp
from app.core.utils.decorators import admin_required


@admin_api_bp.route('/settings/mail', methods=['GET'])
@admin_required
def api_get_mail_config():
    """获取邮件配置"""
    if not session.get('is_admin'):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    conn = get_db()
    config_rows = conn.execute(
        'SELECT config_key, config_value, description FROM system_config WHERE config_key LIKE "mail_%" ORDER BY config_key'
    ).fetchall()
    
    mail_config = {}
    for row in config_rows:
        key = row['config_key']
        value = row['config_value']
        # 对于密码字段，不返回实际值
        if 'password' in key.lower():
            mail_config[key] = '***' if value else ''
        else:
            mail_config[key] = value
    
    return jsonify({
        'status': 'success',
        'data': mail_config
    })



@admin_api_bp.route('/settings/mail', methods=['POST'])
@admin_required
def api_save_mail_config():
    """保存邮件配置"""
    if not session.get('is_admin'):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        conn = get_db()
        user_id = session.get('user_id')
        
        # 邮件配置字段
        mail_fields = {
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
        
        # 保存或更新配置
        for key, description in mail_fields.items():
            value = data.get(key, '')
            
            # 如果是密码字段且值为***或空，则不更新（保持原值）
            if 'password' in key.lower():
                if value == '***' or value == '':
                    current_app.logger.debug(f'跳过更新密码字段 {key}（保持原值）')
                    continue
                # 记录实际长度用于调试
                current_app.logger.info(f'保存授权码，长度: {len(value)}')
            
            # 验证授权码长度（至少6位）
            if key == 'mail_password' and value and value != '***':
                if len(value) < 6:
                    return jsonify({
                        'status': 'error',
                        'message': '邮箱授权码长度至少需要6位，请检查是否正确输入'
                    }), 400
                # 记录保存前的长度
                current_app.logger.info(f'准备保存授权码，长度: {len(value)}')
            
            # 转换布尔值
            if key in ['mail_use_tls', 'mail_use_ssl', 'mail_enabled', 'mail_console_output']:
                value = 'true' if value in [True, 'true', '1', 1] else 'false'
            
            # 转换整数
            if key == 'mail_port':
                try:
                    value = str(int(value))
                except:
                    value = '587'
            
            # 使用 INSERT OR REPLACE 更新配置
            conn.execute('''
                INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value), description, user_id))
        
        conn.commit()
        
        return jsonify({
            'status': 'success',
            'message': '邮件配置保存成功'
        })
    except Exception as e:
        current_app.logger.error(f'保存邮件配置失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'保存失败: {str(e)}'
        }), 500



@admin_api_bp.route('/settings/mail/test', methods=['POST'])
@limiter.limit("5 per minute")  # 测试邮件限制：每分钟5次
@admin_required
def api_test_mail_config():
    """测试邮件配置"""
    if not session.get('is_admin'):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        test_email = data.get('email')
        if not test_email:
            return jsonify({'status': 'error', 'message': '请提供测试邮箱地址'}), 400
        
        # 临时保存配置到数据库
        conn = get_db()
        user_id = session.get('user_id')
        
        mail_fields = {
            'mail_server': data.get('mail_server', ''),
            'mail_port': data.get('mail_port', '587'),
            'mail_use_tls': data.get('mail_use_tls', True),
            'mail_use_ssl': data.get('mail_use_ssl', False),
            'mail_username': data.get('mail_username', ''),
            'mail_password': data.get('mail_password', ''),
            'mail_default_sender': data.get('mail_default_sender', ''),
            'mail_default_sender_name': data.get('mail_default_sender_name', '系统通知'),
        }
        
        for key, value in mail_fields.items():
            if 'password' in key.lower() and value == '***':
                continue
            if key in ['mail_use_tls', 'mail_use_ssl']:
                value = 'true' if value in [True, 'true', '1', 1] else 'false'
            if key == 'mail_port':
                value = str(int(value)) if str(value).isdigit() else '587'
            
            conn.execute('''
                INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_by, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value), '临时测试配置', user_id))
        
        conn.commit()
        
        # 发送测试邮件（强制关闭控制台输出，确保发送真实邮件）
        # 临时设置控制台输出为false
        conn.execute('''
            INSERT OR REPLACE INTO system_config (config_key, config_value, description, updated_by, updated_at)
            VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', ('mail_console_output', 'false', '临时测试配置', user_id))
        conn.commit()
        
        # 验证配置是否完整
        config_check = conn.execute('''
            SELECT config_key, config_value FROM system_config 
            WHERE config_key IN ('mail_server', 'mail_username', 'mail_password', 'mail_default_sender')
        ''').fetchall()
        
        config_dict = {row['config_key']: row['config_value'] for row in config_check}
        missing_configs = []
        if not config_dict.get('mail_server'):
            missing_configs.append('SMTP服务器地址')
        if not config_dict.get('mail_username'):
            missing_configs.append('邮箱用户名')
        if not config_dict.get('mail_password'):
            missing_configs.append('邮箱授权码')
        if not config_dict.get('mail_default_sender'):
            missing_configs.append('默认发件人')
        
        if missing_configs:
            return jsonify({
                'status': 'error',
                'message': f'配置不完整，请填写：{", ".join(missing_configs)}'
            }), 400
        
        from app.core.utils.email_service import EmailService
        code = EmailService.generate_verification_code()
        
        try:
            success, sent_code = EmailService.send_verification_code(
                to_email=test_email,
                code_type='bind',
                code=code
            )
            
            if success and sent_code:
                return jsonify({
                    'status': 'success',
                    'message': f'测试邮件已发送到 {test_email}，验证码：{sent_code}'
                })
            else:
                # 获取更详细的错误信息
                error_msg = '发送失败，请检查配置'
                if not success:
                    error_msg = '邮件发送失败，请检查SMTP配置是否正确（服务器地址、端口、用户名、授权码）'
                elif not sent_code:
                    error_msg = '邮件服务未启用或配置有误'
                
                current_app.logger.error(f'测试邮件发送失败: email={test_email}, success={success}, code={sent_code}')
                return jsonify({
                    'status': 'error',
                    'message': error_msg
                }), 400
        except Exception as e:
            current_app.logger.error(f'测试邮件发送异常: {str(e)}', exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'发送失败: {str(e)}'
            }), 400
    except Exception as e:
        current_app.logger.error(f'测试邮件配置失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'测试失败: {str(e)}'
        }), 500



@admin_api_bp.route('/settings/mail/template-preview', methods=['POST'])
@admin_required
def api_get_mail_template_preview():
    """获取邮件模板预览"""
    if not session.get('is_admin'):
        return jsonify({'status': 'error', 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        template_type = data.get('template_type', 'bind_code')
        
        # 验证模板类型
        valid_types = ['bind_code', 'login_code', 'reset_password']
        if template_type not in valid_types:
            return jsonify({
                'status': 'error',
                'message': f'无效的模板类型，支持的类型: {", ".join(valid_types)}'
            }), 400
        
        # 生成示例验证码
        import secrets
        import string
        digits = string.digits
        sample_code = ''.join(secrets.choice(digits) for _ in range(6))
        sample_email = data.get('email', 'user@example.com')
        
        # 渲染模板
        from app.core.utils.email_templates import render_template
        try:
            html_content = render_template(
                template_type,
                email=sample_email,
                code=sample_code
            )
        except Exception as template_error:
            current_app.logger.error(f'模板渲染失败: {str(template_error)}', exc_info=True)
            return jsonify({
                'status': 'error',
                'message': f'模板渲染失败: {str(template_error)}'
            }), 500
        
        return jsonify({
            'status': 'success',
            'html': html_content,
            'template_type': template_type
        })
        
    except Exception as e:
        current_app.logger.error(f'获取邮件模板预览失败: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'获取预览失败: {str(e)}'
        }), 500

