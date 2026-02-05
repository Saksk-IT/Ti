# -*- coding: utf-8 -*-
"""
RQ 队列工具（最低成本异步任务）

设计目标：
- 未安装 rq/redis 或未配置 Redis 时，调用方能优雅降级。
- Web 端仅负责 enqueue + 查询 job 状态；实际任务由独立 worker 执行。
"""

from __future__ import annotations

from typing import Optional

from .redis_utils import get_redis_connection


def get_queue(name: Optional[str] = None):
    """获取 RQ Queue 对象；失败返回 None。"""
    try:
        from flask import current_app
    except Exception:
        return None

    try:
        from rq import Queue  # type: ignore
    except Exception:
        return None

    conn = get_redis_connection()
    if conn is None:
        return None

    qname = (name or current_app.config.get('RQ_QUEUE_NAME') or 'saksk').strip()
    try:
        return Queue(qname, connection=conn)
    except Exception:
        return None


def fetch_job(job_id: str):
    """按 job_id 获取 Job；失败返回 None。"""
    try:
        from rq.job import Job  # type: ignore
    except Exception:
        return None

    conn = get_redis_connection()
    if conn is None:
        return None

    try:
        return Job.fetch(job_id, connection=conn)
    except Exception:
        return None

