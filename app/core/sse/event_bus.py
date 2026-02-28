# -*- coding: utf-8 -*-
"""SSE 事件总线 — Redis Pub/Sub 优先 + 进程内降级

设计：
- 每个 SSE 连接对应一个 queue.Queue（进程内）
- publish() 有 Redis 时通过 Pub/Sub 广播到所有 worker，否则降级本进程分发
- 守护线程 _listen() 订阅 Redis channel，收到消息后分发到本进程 Queue
- 首次 publish() 时懒初始化 Redis 连接和订阅线程
- Queue 满时静默丢弃，客户端重连会主动拉最新数据
"""
from __future__ import annotations

import json
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

CHANNEL = "sse:events"
MAX_CONNECTIONS_PER_USER = 3
MAX_TOTAL_CONNECTIONS = 200
MAX_CONNECTION_DURATION_SECONDS = 600  # 10 分钟
HEARTBEAT_INTERVAL_SECONDS = 15


@dataclass(frozen=True)
class SSEEvent:
    """不可变 SSE 事件"""
    event: str
    data: str  # JSON string


# ── 进程内订阅管理 ──────────────────────────────────────
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

def get_connection_count(user_id: int) -> int:
    """获取某用户当前的 SSE 连接数"""
    with _lock:
        return len(_subscribers.get(user_id, []))


def get_total_connection_count() -> int:
    """获取当前进程内所有 SSE 连接总数"""
    with _lock:
        return sum(len(qs) for qs in _subscribers.values())


# ── 本进程分发 ──────────────────────────────────────────

def _dispatch_local(
    event_type: str,
    user_ids: Optional[list[int]],
    payload: Optional[dict] = None,
) -> None:
    """将事件分发到本进程内的目标用户队列"""
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


# ── Redis Pub/Sub ───────────────────────────────────────

_redis_ready = False
_redis_init_lock = threading.Lock()
_redis_conn = None


def _ensure_redis() -> bool:
    """懒初始化 Redis 连接和订阅线程。返回 Redis 是否可用。"""
    global _redis_ready, _redis_conn

    if _redis_ready:
        return True

    with _redis_init_lock:
        if _redis_ready:
            return True

        try:
            from app.core.utils.redis_utils import get_redis_connection
            conn = get_redis_connection()
            if conn is None:
                return False
            # 测试连通性
            conn.ping()
            _redis_conn = conn

            # 启动订阅守护线程
            t = threading.Thread(target=_listen, daemon=True)
            t.start()

            _redis_ready = True
            logger.info("SSE event_bus: Redis Pub/Sub 已启用")
            return True
        except Exception as e:
            logger.debug("SSE event_bus: Redis 不可用，降级进程内分发: %s", e)
            return False


def _listen() -> None:
    """Redis 订阅守护线程：监听 channel，收到消息后分发到本进程队列"""
    try:
        from app.core.utils.redis_utils import get_redis_connection
        conn = get_redis_connection()
        if conn is None:
            return
        pubsub = conn.pubsub()
        pubsub.subscribe(CHANNEL)
        for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                raw = message["data"]
                if isinstance(raw, (bytes, bytearray)):
                    raw = raw.decode("utf-8")
                obj = json.loads(raw)
                event_type = obj.get("event", "")
                user_ids = obj.get("user_ids")
                payload = obj.get("payload")
                _dispatch_local(event_type, user_ids, payload)
            except Exception:
                pass
    except Exception as e:
        global _redis_ready
        _redis_ready = False
        logger.warning("SSE event_bus: Redis 订阅线程退出: %s", e)


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
    if _ensure_redis() and _redis_conn is not None:
        try:
            msg = json.dumps({
                "event": event_type,
                "user_ids": user_ids,
                "payload": payload or {},
            }, ensure_ascii=False)
            _redis_conn.publish(CHANNEL, msg)
            return
        except Exception:
            pass  # Redis 发布失败，降级本进程分发

    _dispatch_local(event_type, user_ids, payload)
