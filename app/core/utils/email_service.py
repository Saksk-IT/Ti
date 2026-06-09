# -*- coding: utf-8 -*-
"""
邮件服务工具
提供验证码生成和邮件发送功能
"""
import smtplib
import secrets
import string
import re
import logging
from typing import Optional, Dict, Any, Tuple
from flask import current_app
from app.core.utils.email_templates import render_template, get_email_subject

logger = logging.getLogger(__name__)


class EmailService:
    """邮件服务类"""

    @staticmethod
    def _get_code_length() -> int:
        """
        从 system_config 表读取验证码长度配置

        Returns:
            验证码长度（4-8，默认6）
        """
        try:
            from app.models.system import SystemConfig
            row = SystemConfig.query.filter_by(
                config_key='mail_verification_code_length'
            ).first()
            if row:
                val = int(row.config_value)
                if 4 <= val <= 8:
                    return val
        except Exception as exc:
            logger.warning('读取验证码长度配置失败，使用默认值: %s', exc)
        return 6

    @staticmethod
    def generate_verification_code(length: int | None = None) -> str:
        """
        生成验证码

        Args:
            length: 验证码长度，为 None 时从配置读取（默认6位）

        Returns:
            验证码字符串（纯数字）
        """
        if length is None:
            length = EmailService._get_code_length()
        # 使用安全的随机数生成器
        digits = string.digits
        code = ''.join(secrets.choice(digits) for _ in range(length))
        return code
    
    @staticmethod
    def _get_smtp_config() -> Dict[str, Any]:
        """
        获取SMTP配置
        优先从后台系统配置读取，如果不存在则从环境变量读取
        
        Returns:
            SMTP配置字典
        """
        try:
            from app.modules.admin.services.system_config_service import SystemConfigService

            mail_config = SystemConfigService.get_mail_config()
            if mail_config.get('server'):
                return {
                    'server': mail_config.get('server'),
                    'port': mail_config.get('port', 587),
                    'use_tls': mail_config.get('use_tls', True),
                    'use_ssl': mail_config.get('use_ssl', False),
                    'username': mail_config.get('username'),
                    'password': mail_config.get('password'),
                    'sender': mail_config.get('sender'),
                    'sender_name': mail_config.get('sender_name', '系统通知'),
                }
        except Exception as e:
            current_app.logger.warning(f'从后台系统设置读取邮件配置失败，使用环境变量: {str(e)}')
        
        # 如果数据库中没有配置，使用环境变量
        return {
            'server': current_app.config.get('MAIL_SERVER'),
            'port': current_app.config.get('MAIL_PORT', 587),
            'use_tls': current_app.config.get('MAIL_USE_TLS', True),
            'use_ssl': current_app.config.get('MAIL_USE_SSL', False),
            'username': current_app.config.get('MAIL_USERNAME'),
            'password': current_app.config.get('MAIL_PASSWORD'),
            'sender': current_app.config.get('MAIL_DEFAULT_SENDER'),
            'sender_name': current_app.config.get('MAIL_DEFAULT_SENDER_NAME', '系统通知'),
        }
    
    @staticmethod
    def _render_email_template(template_type: str, **kwargs) -> Tuple[str, str]:
        """
        渲染邮件模板
        
        Args:
            template_type: 模板类型（bind_code, login_code, reset_password）
            **kwargs: 模板变量
            
        Returns:
            (subject, body) 元组
        """
        # 验证模板类型
        valid_types = ['bind_code', 'login_code', 'reset_password']
        if template_type not in valid_types:
            raise ValueError(f"未知的模板类型: {template_type}，支持的类型: {', '.join(valid_types)}")
        
        try:
            # 获取邮件主题
            subject = get_email_subject(template_type)
            
            # 渲染邮件正文
            body = render_template(template_type, **kwargs)
            
            return subject, body
        except Exception as e:
            current_app.logger.error(f'邮件模板渲染失败: template_type={template_type}, error={str(e)}', exc_info=True)
            raise
    
    @staticmethod
    def _send_email_smtp(to_email: str, subject: str, body_html: str) -> bool:
        """
        通过SMTP发送邮件（同步，Flask context 下使用）

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body_html: 邮件正文（HTML格式）

        Returns:
            是否发送成功
        """
        config = EmailService._get_smtp_config()
        try:
            from app.tasks.email_tasks import smtp_send_pure
            smtp_send_pure(to_email, subject, body_html, config)
            current_app.logger.info(f'邮件发送成功: {to_email}')
            return True
        except ValueError as e:
            current_app.logger.error(f'邮件配置错误: {e}, to_email={to_email}')
            return False
        except smtplib.SMTPAuthenticationError as e:
            current_app.logger.error(f'SMTP认证失败: {e}, to_email={to_email}, username={config.get("username")}')
            return False
        except (smtplib.SMTPException, ConnectionError, OSError) as e:
            error_type = type(e).__name__
            current_app.logger.error(f'SMTP连接错误: {e} ({error_type}), to_email={to_email}, server={config.get("server")}:{config.get("port")}')
            if 'Connection unexpectedly closed' in str(e) or 'Connection closed' in str(e):
                current_app.logger.error('可能的原因: 1) 授权码错误或已过期 2) SMTP服务未开启 3) 163邮箱需要验证码登录 4) 网络连接问题')
            return False
        except Exception as e:
            error_type = type(e).__name__
            current_app.logger.error(f'邮件发送失败: {e} ({error_type}), to_email={to_email}', exc_info=True)
            return False

    @staticmethod
    def _send_email_smtp_with_config(
        to_email: str, subject: str, body_html: str, config: Dict[str, Any]
    ) -> bool:
        """
        使用指定配置发送邮件（不读取数据库/环境变量，用于测试接口）

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            body_html: 邮件正文（HTML格式）
            config: SMTP 配置字典，包含 server/port/use_tls/use_ssl/username/password/sender/sender_name

        Returns:
            是否发送成功
        """
        try:
            from app.tasks.email_tasks import smtp_send_pure
            smtp_send_pure(to_email, subject, body_html, config)
            current_app.logger.info(f'测试邮件发送成功: {to_email}')
            return True
        except ValueError as e:
            current_app.logger.error(f'邮件配置错误: {e}, to_email={to_email}')
            return False
        except smtplib.SMTPAuthenticationError as e:
            current_app.logger.error(f'SMTP认证失败: {e}, to_email={to_email}')
            return False
        except (smtplib.SMTPException, ConnectionError, OSError) as e:
            current_app.logger.error(f'SMTP连接错误: {e}, to_email={to_email}')
            return False
        except Exception as e:
            current_app.logger.error(f'邮件发送失败: {e}, to_email={to_email}', exc_info=True)
            return False

    @staticmethod
    def _console_output_code(to_email: str, code: str, template_type: str) -> None:
        """
        在控制台输出验证码（开发环境使用）
        
        Args:
            to_email: 收件人邮箱
            code: 验证码
            template_type: 模板类型
        """
        logger.info(
            '\n' + '=' * 60 + '\n'
            '邮件服务（开发模式 - 控制台输出）\n'
            + '=' * 60 + '\n'
            f'收件人: {to_email}\n'
            f'类型: {template_type}\n'
            f'验证码: {code}\n'
            + '=' * 60
        )
        current_app.logger.info(f'[开发模式] 验证码已输出到控制台: {to_email} -> {code}')
    
    @staticmethod
    def send_verification_code(
        to_email: str,
        code_type: str,
        code: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        发送验证码邮件
        
        Args:
            to_email: 收件人邮箱
            code_type: 验证码类型（bind, login, reset_password）
            code: 验证码（如果为None则自动生成）
            
        Returns:
            (是否成功, 验证码) 元组
        """
        # 生成验证码
        if code is None:
            code = EmailService.generate_verification_code()
        
        try:
            from app.modules.admin.services.system_config_service import SystemConfigService

            mail_config = SystemConfigService.get_mail_config()
            mail_enabled = bool(mail_config.get('enabled', True))
            console_output = bool(mail_config.get('console_output', False))
        except Exception:
            mail_enabled = current_app.config.get('MAIL_ENABLED', True)
            console_output = current_app.config.get('MAIL_CONSOLE_OUTPUT', False)
        
        if not mail_enabled:
            current_app.logger.warning(f'邮件服务未启用: to_email={to_email}, code_type={code_type}')
            return False, None
        
        # 如果启用控制台输出，则只输出到控制台，不发送真实邮件
        if console_output:
            EmailService._console_output_code(to_email, code, code_type)
            return True, code
        
        # 渲染邮件模板
        template_type_map = {
            'bind': 'bind_code',
            'login': 'login_code',
            'reset_password': 'reset_password'
        }
        
        template_type = template_type_map.get(code_type)
        if not template_type:
            current_app.logger.error(f'未知的验证码类型: {code_type}, to_email={to_email}')
            return False, None
        
        try:
            subject, body_html = EmailService._render_email_template(
                template_type,
                email=to_email,
                code=code
            )
        except Exception as e:
            current_app.logger.error(f'邮件模板渲染失败: {str(e)}', exc_info=True)
            return False, None
        
        # 尝试 RQ 异步发送，不可用时降级为同步
        try:
            from app.core.utils.rq_utils import get_queue
            queue = get_queue()
        except Exception:
            queue = None

        if queue is not None:
            try:
                from rq import Retry  # type: ignore
                smtp_config = EmailService._get_smtp_config()
                queue.enqueue(
                    'app.tasks.email_tasks.send_email_task',
                    to_email=to_email,
                    subject=subject,
                    body_html=body_html,
                    config=smtp_config,
                    retry=Retry(max=3, interval=[30, 60, 120]),
                    job_timeout=120,
                    ttl=600,
                    on_failure='app.tasks.email_tasks.on_email_task_failure',
                )
                current_app.logger.info(
                    f'验证码邮件已入队(异步): {to_email}, code_type={code_type}'
                )
                return True, code
            except Exception as e:
                current_app.logger.warning(
                    f'RQ 入队失败，降级为同步发送: {e}'
                )

        # 降级：同步发送
        success = EmailService._send_email_smtp(to_email, subject, body_html)

        if success:
            current_app.logger.info(f'验证码邮件发送成功(同步): {to_email}, code_type={code_type}')
            return True, code
        else:
            current_app.logger.error(f'验证码邮件发送失败: {to_email}, code_type={code_type}')
            return False, None
    
    @staticmethod
    def validate_email_format(email: str) -> bool:
        """
        验证邮箱格式
        
        Args:
            email: 邮箱地址
            
        Returns:
            是否为有效邮箱格式
        """
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
