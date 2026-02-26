# -*- coding: utf-8 -*-
"""SSE 流端点"""
from __future__ import annotations

import queue

from flask import Blueprint, Response, session, stream_with_context, jsonify

from .event_bus import subscribe, unsubscribe, get_connection_count, SSEEvent

sse_bp = Blueprint('sse', __name__)


def _format_sse(event: str, data: str) -> str:
    """格式化为 SSE 协议文本"""
    return f"event: {event}\ndata: {data}\n\n"


@sse_bp.route('/sse/stream')
def sse_stream():
    """SSE 长连接端点

    - 已登录用户建立连接后，持续接收推送事件
    - 25 秒无事件发送心跳注释行（防止代理/浏览器超时）
    - 客户端断开时自动清理订阅
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'unauthorized', 'message': '请先登录'}), 401

    uid = int(user_id)

    # S3: 限制每用户最大 SSE 连接数
    if get_connection_count(uid) >= 3:
        return jsonify({'status': 'error', 'message': '连接数超限，请关闭其他标签页'}), 429

    def generate():
        q = subscribe(uid)
        try:
            yield _format_sse('connected', '{}')
            while True:
                try:
                    evt: SSEEvent = q.get(timeout=25)
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
