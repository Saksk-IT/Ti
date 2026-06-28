# -*- coding: utf-8 -*-
"""SSE 流端点"""
from __future__ import annotations

import json
import queue
import time

from flask import Blueprint, Response, session, stream_with_context, jsonify, current_app

from .event_bus import (
    subscribe, unsubscribe, get_connection_count, get_total_connection_count,
    SSEEvent, MAX_TOTAL_CONNECTIONS, MAX_CONNECTION_DURATION_SECONDS,
    HEARTBEAT_INTERVAL_SECONDS, MAX_CONNECTIONS_PER_USER,
)

sse_bp = Blueprint('sse', __name__)


def _format_sse(event: str, data: str) -> str:
    """格式化为 SSE 协议文本"""
    return f"event: {event}\ndata: {data}\n\n"


def _retry_after_seconds() -> int:
    """获取 SSE 拒绝重试间隔（秒）"""
    return max(1, int(current_app.config.get('SSE_RETRY_AFTER_SECONDS', 30) or 30))


def _build_rejected_response(status_code: int, message: str, reason: str):
    """构造拒绝连接响应（包含 Retry-After）"""
    retry_after = _retry_after_seconds()
    resp = jsonify({
        'status': 'error',
        'message': message,
        'reason': reason,
        'retry_after': retry_after,
    })
    resp.status_code = status_code
    resp.headers['Retry-After'] = str(retry_after)
    resp.headers['Cache-Control'] = 'no-store'
    return resp


def _sse_enabled() -> bool:
    """当前应用是否允许建立 SSE 长连接。"""
    return bool(current_app.config.get('SSE_ENABLED', True))


def _validate_sse_capacity(uid: int):
    """校验 SSE 连接容量；通过返回 None，不通过返回 response"""
    if not _sse_enabled():
        return _build_rejected_response(
            status_code=503,
            message='实时推送已关闭，页面将使用轮询刷新',
            reason='disabled',
        )

    # 全局连接数上限
    max_total = current_app.config.get('SSE_MAX_TOTAL_CONNECTIONS', MAX_TOTAL_CONNECTIONS)
    if get_total_connection_count() >= max_total:
        return _build_rejected_response(
            status_code=503,
            message='服务器连接数已满，请稍后重试',
            reason='total_connection_limit',
        )

    # 每用户最大连接数
    max_per_user = current_app.config.get('SSE_MAX_CONNECTIONS_PER_USER', MAX_CONNECTIONS_PER_USER)
    if get_connection_count(uid) >= max_per_user:
        return _build_rejected_response(
            status_code=429,
            message='连接数超限，请关闭其他标签页',
            reason='per_user_connection_limit',
        )

    return None


@sse_bp.route('/sse/preflight')
def sse_preflight():
    """SSE 连接前预检，用于客户端决定是否立即重连"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(user_id)
    rejected = _validate_sse_capacity(uid)
    if rejected is not None:
        return rejected

    resp = jsonify({
        'status': 'success',
        'can_connect': True,
        'retry_after': 0,
    })
    resp.headers['Cache-Control'] = 'no-store'
    return resp


@sse_bp.route('/sse/stream')
def sse_stream():
    """SSE 长连接端点

    - 已登录用户建立连接后，持续接收推送事件
    - 15 秒无事件发送心跳注释行（防止代理/浏览器超时）
    - 生产可通过 SSE_ENABLED=false 快速关闭，客户端自动降级轮询
    - 全局连接数上限 200，超限返回 503
    - 最大连接时长 10 分钟，到期发送 reconnect 事件
    - 客户端断开时自动清理订阅
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(user_id)

    rejected = _validate_sse_capacity(uid)
    if rejected is not None:
        return rejected

    max_duration = current_app.config.get('SSE_MAX_CONNECTION_DURATION_SECONDS', MAX_CONNECTION_DURATION_SECONDS)
    heartbeat_interval = current_app.config.get('SSE_HEARTBEAT_INTERVAL_SECONDS', HEARTBEAT_INTERVAL_SECONDS)

    def generate():
        q = subscribe(uid)
        start_time = time.monotonic()
        try:
            yield _format_sse('connected', '{}')
            while True:
                # 检查最大连接时长
                elapsed = time.monotonic() - start_time
                if elapsed >= max_duration:
                    yield _format_sse('reconnect', json.dumps({'reason': 'max_duration'}))
                    break

                try:
                    evt: SSEEvent = q.get(timeout=heartbeat_interval)
                    yield _format_sse(evt.event, evt.data)
                except queue.Empty:
                    yield ': heartbeat\n\n'
        except GeneratorExit:
            pass
        finally:
            unsubscribe(uid, q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
