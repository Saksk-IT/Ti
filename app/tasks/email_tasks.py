# -*- coding: utf-8 -*-
"""
邮件发送任务（用于 RQ worker）

注意：
- 任务函数不依赖 Flask current_app（避免 worker 需要 app_context）。
- SMTP 配置以 dict 形式由 enqueue 方序列化传入。
- 失败时 raise，由 RQ Retry 机制自动重试。
- 最终重试全部失败后，记录到 Redis 提供可观测性。
"""

from __future__ import annotations

import logging
import smtplib
import time
from email.header import Header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from typing import Any, Dict

logger = logging.getLogger(__name__)


def smtp_send_pure(
    to_email: str,
    subject: str,
    body_html: str,
    config: Dict[str, Any],
) -> None:
    """纯函数 SMTP 发送，不依赖 Flask context。

    Args:
        to_email: 收件人邮箱
        subject: 邮件主题
        body_html: 邮件正文（HTML）
        config: SMTP 配置字典，包含 server/port/use_tls/use_ssl/
                username/password/sender/sender_name

    Raises:
        ValueError: 配置不完整
        smtplib.SMTPException: SMTP 发送失败
        ConnectionError/OSError: 网络连接失败
    """
    missing = [k for k in ('server', 'username', 'password') if not config.get(k)]
    if missing:
        raise ValueError(f'SMTP 配置不完整，缺少: {", ".join(missing)}')

    sender_email = config.get('sender') or config['username']
    if not sender_email:
        raise ValueError('发件人邮箱未配置')

    # 构建邮件
    msg = MIMEMultipart('alternative')
    msg['From'] = formataddr((config.get('sender_name', '系统通知'), sender_email))
    msg['To'] = to_email
    msg['Subject'] = Header(subject, 'utf-8')
    msg.attach(MIMEText(body_html, 'html', 'utf-8'))

    # 连接并发送
    conn_timeout = 30
    server = None
    try:
        if config.get('use_ssl'):
            server = smtplib.SMTP_SSL(config['server'], config['port'], timeout=conn_timeout)
        else:
            server = smtplib.SMTP(config['server'], config['port'], timeout=conn_timeout)

        server.timeout = 60

        if config.get('use_tls') and not config.get('use_ssl'):
            server.starttls()

        server.login(config['username'], config['password'])
        server.send_message(msg)
        server.quit()
        server = None

        logger.info('邮件发送成功: %s', to_email)
    finally:
        if server is not None:
            try:
                server.quit()
            except Exception:
                try:
                    server.close()
                except Exception:
                    pass


def _record_failure(to_email: str, subject: str, error: str) -> None:
    """最终重试全部失败后，记录到 Redis 提供可观测性。

    key: email:failed:{timestamp}，TTL 7 天。
    """
    try:
        import json

        from app.core.utils.redis_utils import get_redis_connection, get_redis_url_from_env

        conn = get_redis_connection(get_redis_url_from_env())
        if conn is None:
            return
        key = f'email:failed:{int(time.time())}'
        payload = json.dumps(
            {'to': to_email, 'subject': subject, 'error': error},
            ensure_ascii=False,
        )
        conn.set(key, payload, ex=7 * 24 * 60 * 60)  # TTL 7 天
    except Exception as exc:
        logger.warning('记录邮件发送失败到 Redis 失败: %s', exc)


def send_email_task(
    *,
    to_email: str,
    subject: str,
    body_html: str,
    config: Dict[str, Any],
) -> None:
    """RQ 邮件发送任务入口。

    由 EmailService.send_verification_code 通过 enqueue 调用。
    失败时 raise 触发 RQ Retry；最终失败通过 on_failure 回调记录到 Redis。
    """
    smtp_send_pure(to_email, subject, body_html, config)


def on_email_task_failure(job: Any, connection: Any, typ: Any, value: Any, traceback: Any) -> None:
    """RQ on_failure 回调 — 所有重试用尽后由 RQ 调用。"""
    kwargs = job.kwargs or {}
    to_email = kwargs.get('to_email', 'unknown')
    subject = kwargs.get('subject', 'unknown')
    logger.error('邮件发送最终失败: to=%s, error=%s', to_email, value)
    _record_failure(to_email, subject, str(value))
