# -*- coding: utf-8 -*-
"""
短信发送任务（用于 RQ worker）

注意：
- 任务函数不依赖 Flask current_app（避免 worker 需要 app_context）。
- 阿里云配置以 dict 形式由 enqueue 方序列化传入。
- 失败时 raise，由 RQ Retry 机制自动重试。
- 最终重试全部失败后，记录到 Redis 提供可观测性。
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


def send_sms_task(
    *,
    phone: str,
    config: Dict[str, Any],
) -> None:
    """RQ 短信发送任务入口。

    由 SmsAuthService 通过 enqueue 调用。
    失败时 raise 触发 RQ Retry；最终失败通过 on_failure 回调记录到 Redis。
    """
    from app.core.utils.sms_service import send_sms_verify_code

    result = send_sms_verify_code(phone, config)
    if not result.success:
        raise RuntimeError(
            f'短信发送失败: phone={phone}, '
            f'error_code={result.error_code}, '
            f'error_message={result.error_message}'
        )
    logger.info('短信发送成功(RQ): phone=%s, biz_id=%s', phone, result.biz_id)


def on_sms_task_failure(
    job: Any, connection: Any, typ: Any, value: Any, traceback: Any
) -> None:
    """RQ on_failure 回调 — 所有重试用尽后由 RQ 调用。"""
    kwargs = job.kwargs or {}
    phone = kwargs.get('phone', 'unknown')
    logger.error('短信发送最终失败: phone=%s, error=%s', phone, value)
    _record_failure(phone, str(value))


def _record_failure(phone: str, error: str) -> None:
    """最终重试全部失败后，记录到 Redis 提供可观测性。

    key: sms:failed:{timestamp}，TTL 7 天。
    """
    try:
        import json

        from app.core.utils.redis_utils import get_redis_connection, get_redis_url_from_env

        conn = get_redis_connection(get_redis_url_from_env())
        if conn is None:
            return
        key = f'sms:failed:{int(time.time())}'
        payload = json.dumps(
            {'phone': phone, 'error': error},
            ensure_ascii=False,
        )
        conn.set(key, payload, ex=7 * 24 * 60 * 60)
    except Exception as exc:
        logger.warning('记录短信发送失败到 Redis 失败: %s', exc)
