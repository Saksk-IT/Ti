# -*- coding: utf-8 -*-
"""进程内 SSE 事件总线

设计：
- 每个 SSE 连接对应一个 queue.Queue
- publish() 将事件 put 到目标用户的所有 queue
- 广播（user_ids=None）遍历所有在线用户
- Queue 满时静默丢弃，客户端重连会主动拉最新数据
"""
from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class SSEEvent:
    """不可变 SSE 事件"""
    event: str
    data: str  # JSON string


_lock = threading.Lock()
_subscribers: dict[int, list[queue.Queue[SSEEvent]]] = {}


def subscribe(user_id: int) -> queue.Queue[SSEEvent]:
    """注册 SSE 连接，返回该连接的事件队列"""
    q: queue.Queue[SSEEvent] = queue.Queue(maxsize=64)
    with _lock:
        _subscribers.setdefault(user_id, []).append(q)
    return q


def unsubscribe(user_id: int, q: queue.Queue[SSEEvent]) -> None:
    """注销 SSE 连接"""
    with _lock:
        qs = _subscribers.get(user_id)
        if qs is None:
            return
        try:
            qs.remove(q)
        except ValueError:
            pass
        if not qs:
            _subscribers.pop(user_id, None)


def publish(
    event_type: str,
    user_ids: Optional[list[int]],
    payload: Optional[dict] = None,
) -> None:
    """发布事件到目标用户的 SSE 队列

    Args:
        event_type: 事件名称
        user_ids: 目标用户列表；None 表示广播给所有在线用户
        payload: 事件数据（会序列化为 JSON）
    """
    data_str = json.dumps(payload or {}, ensure_ascii=False)
    evt = SSEEvent(event=event_type, data=data_str)

    with _lock:
        if user_ids is None:
            target_queues = [
                q for qs in _subscribers.values() for q in qs
            ]
        else:
            target_queues = [
                q
                for uid in user_ids
                for q in _subscribers.get(uid, [])
            ]

    for q in target_queues:
        try:
            q.put_nowait(evt)
        except queue.Full:
            pass  # 丢弃，客户端重连时拉最新
