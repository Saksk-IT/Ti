# -*- coding: utf-8 -*-
"""教务上游请求的全局限流与抢先成功执行器。"""

from __future__ import annotations

import concurrent.futures
import secrets
import threading
import time
from typing import Callable, List, Optional

from .client import ScheduleAuthError, ScheduleClientError


_GLOBAL_CONCURRENCY = 20
_GLOBAL_SEMAPHORE = threading.BoundedSemaphore(_GLOBAL_CONCURRENCY)
_REDIS_KEY = "edu_schedule:upstream_slots"
_REDIS_TTL_SECONDS = 120
_SLOT_WAIT_SECONDS = 0.05
_ACQUIRE_SCRIPT = """
local key = KEYS[1]
local limit = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])
local token = ARGV[3]
local now = tonumber(ARGV[4])
redis.call('ZREMRANGEBYSCORE', key, '-inf', now - ttl)
if redis.call('ZCARD', key) < limit then
  redis.call('ZADD', key, now, token)
  redis.call('EXPIRE', key, ttl)
  return 1
end
return 0
"""


def run_with_global_upstream_slot(fetch_once: Callable, redis_connection=None):
    if redis_connection is not None:
        token = secrets.token_urlsafe(18)
        acquired = False
        try:
            while not acquired:
                raw_acquired = redis_connection.eval(
                    _ACQUIRE_SCRIPT,
                    1,
                    _REDIS_KEY,
                    _GLOBAL_CONCURRENCY,
                    _REDIS_TTL_SECONDS,
                    token,
                    time.time(),
                )
                acquired = int(raw_acquired or 0) == 1
                if not acquired:
                    time.sleep(_SLOT_WAIT_SECONDS)
            return fetch_once()
        except Exception:
            if acquired:
                raise
        finally:
            if acquired:
                try:
                    redis_connection.zrem(_REDIS_KEY, token)
                except Exception:
                    pass

    _GLOBAL_SEMAPHORE.acquire()
    try:
        return fetch_once()
    finally:
        _GLOBAL_SEMAPHORE.release()


def fetch_first_success(
    fetch_once: Callable,
    *,
    task_concurrency: int,
    run_with_slot: Callable,
    cleanup_result: Optional[Callable] = None,
):
    worker_count = max(1, min(int(task_concurrency), _GLOBAL_CONCURRENCY))
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=worker_count,
        thread_name_prefix="edu-upstream",
    )
    futures = [executor.submit(run_with_slot, fetch_once) for _ in range(worker_count)]
    errors: List[Exception] = []
    try:
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                if cleanup_result is not None:
                    for other_future in futures:
                        if other_future is not future:
                            other_future.add_done_callback(
                                lambda completed, cleanup=cleanup_result: _cleanup_future_result(
                                    completed,
                                    cleanup,
                                )
                            )
                return result
            except Exception as exc:
                errors.append(exc)
        raise _select_error(errors)
    finally:
        for future in futures:
            if not future.done():
                future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)


def _select_error(errors: List[Exception]) -> Exception:
    for exc in errors:
        if isinstance(exc, ScheduleAuthError):
            return exc
    return errors[-1] if errors else ScheduleClientError("教务查询失败，请稍后重试")


def _cleanup_future_result(future, cleanup_result: Callable) -> None:
    try:
        result = future.result()
    except Exception:
        return
    try:
        cleanup_result(result)
    except Exception:
        return
