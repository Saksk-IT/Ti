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
    HEARTBEAT_INTERVAL_SECONDS,
)

sse_bp = Blueprint('sse', __name__)


def _format_sse(event: str, data: str) -> str:
    """格式化为 SSE 协议文本"""
    return f"event: {event}\ndata: {data}\n\n"


@sse_bp.route('/sse/stream')
def sse_stream():
    """SSE 长连接端点

    - 已登录用户建立连接后，持续接收推送事件
    - 15 秒无事件发送心跳注释行（防止代理/浏览器超时）
    - 全局连接数上限 200，超限返回 503
    - 最大连接时长 10 分钟，到期发送 reconnect 事件
    - 客户端断开时自动清理订阅
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(user_id)

    # 全局连接数上限
    max_total = current_app.config.get('SSE_MAX_TOTAL_CONNECTIONS', MAX_TOTAL_CONNECTIONS)
    if get_total_connection_count() >= max_total:
        return jsonify({'status': 'error', 'message': '服务器连接数已满，请稍后重试'}), 503

    # 每用户最大连接数
    if get_connection_count(uid) >= 3:
        return jsonify({'status': 'error', 'message': '连接数超限，请关闭其他标签页'}), 429

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
