# -*- coding: utf-8 -*-
"""教务查询任务的 Redis 原子协调。"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple


class QueryTaskCoordinationError(RuntimeError):
    """Redis 任务协调不可用或状态损坏。"""


_ALLOCATE_REFRESH_ORDER_SCRIPT = """
local key = KEYS[1]
local ttl = tonumber(ARGV[1])
local redis_time = redis.call('TIME')
local now_us = tonumber(redis_time[1]) * 1000000 + tonumber(redis_time[2])
local previous = tonumber(redis.call('GET', key) or '0')
local next_value = now_us
if next_value <= previous then
  next_value = previous + 1
end
redis.call('SET', key, string.format('%.0f', next_value), 'EX', ttl)
return string.format('%.0f', next_value)
"""


_REGISTER_OR_COALESCE_SCRIPT = """
local dedupe_key = KEYS[1]
local candidate_key = KEYS[2]
local task_prefix = ARGV[1]
local candidate_id = ARGV[2]
local candidate_payload = ARGV[3]
local ttl = tonumber(ARGV[4])

local existing_id = redis.call('GET', dedupe_key)
if existing_id then
  local existing_key = task_prefix .. existing_id
  local existing_payload = redis.call('GET', existing_key)
  if existing_payload then
    local ok, existing = pcall(cjson.decode, existing_payload)
    if ok and (
      existing['status'] == 'pending' or
      existing['status'] == 'running' or
      existing['status'] == 'retrying'
    ) then
      redis.call('EXPIRE', existing_key, ttl)
      redis.call('EXPIRE', dedupe_key, ttl)
      return {0, existing_payload}
    end
  end
end

redis.call('SET', candidate_key, candidate_payload, 'EX', ttl)
redis.call('SET', dedupe_key, candidate_id, 'EX', ttl)
return {1, candidate_payload}
"""


_TRANSITION_STATE_SCRIPT = """
local task_key = KEYS[1]
local dedupe_key = KEYS[2]
local next_payload = ARGV[1]
local ttl = tonumber(ARGV[2])
local task_id = ARGV[3]
local next_status = ARGV[4]
local next_publish_claimed = ARGV[5] == '1'

local current_payload = redis.call('GET', task_key)
if not current_payload then
  return {0, ''}
end
local ok, current = pcall(cjson.decode, current_payload)
if not ok then
  return {-1, current_payload}
end
local current_status = current['status']
if current_status == 'cancelled' or current_status == 'succeeded' or current_status == 'failed' then
  return {1, current_payload}
end
if current['publish_claimed'] == true and next_status ~= 'succeeded' and next_status ~= 'failed' then
  return {1, current_payload}
end

redis.call('SET', task_key, next_payload, 'EX', ttl)
local dedupe_owner = redis.call('GET', dedupe_key)
if next_publish_claimed then
  if dedupe_owner == task_id then
    redis.call('DEL', dedupe_key)
  end
elseif next_status == 'pending' or next_status == 'running' or next_status == 'retrying' then
  if not dedupe_owner or dedupe_owner == task_id then
    redis.call('SET', dedupe_key, task_id, 'EX', ttl)
  end
elseif dedupe_owner == task_id then
  redis.call('DEL', dedupe_key)
end
return {1, next_payload}
"""


def _decode_text(value: Any) -> str:
    if isinstance(value, (bytes, bytearray)):
        return value.decode("utf-8")
    return str(value or "")


def _decode_state(value: Any) -> Dict[str, Any]:
    try:
        state = json.loads(_decode_text(value))
    except (TypeError, ValueError, UnicodeDecodeError) as exc:
        raise QueryTaskCoordinationError("Redis 查询任务状态损坏") from exc
    if not isinstance(state, dict) or not state.get("task_id"):
        raise QueryTaskCoordinationError("Redis 查询任务状态损坏")
    return state


def _dump_state(state: Dict[str, Any]) -> str:
    try:
        return json.dumps(
            state,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise QueryTaskCoordinationError("查询任务状态无法序列化") from exc


def allocate_refresh_order(connection, key: str, ttl_seconds: int) -> int:
    try:
        raw_value = connection.eval(
            _ALLOCATE_REFRESH_ORDER_SCRIPT,
            1,
            key,
            int(ttl_seconds),
        )
        refresh_order = int(_decode_text(raw_value))
    except Exception as exc:
        raise QueryTaskCoordinationError("Redis 无法分配成绩刷新顺序") from exc
    if refresh_order <= 0:
        raise QueryTaskCoordinationError("Redis 返回的成绩刷新顺序无效")
    return refresh_order


def register_or_coalesce(
    connection,
    *,
    dedupe_key: str,
    task_key: str,
    task_key_prefix: str,
    state: Dict[str, Any],
    ttl_seconds: int,
) -> Tuple[bool, Dict[str, Any]]:
    payload = _dump_state(state)
    try:
        raw_result = connection.eval(
            _REGISTER_OR_COALESCE_SCRIPT,
            2,
            dedupe_key,
            task_key,
            task_key_prefix,
            str(state["task_id"]),
            payload,
            int(ttl_seconds),
        )
    except Exception as exc:
        raise QueryTaskCoordinationError("Redis 无法创建教务查询任务") from exc
    if not isinstance(raw_result, (list, tuple)) or len(raw_result) != 2:
        raise QueryTaskCoordinationError("Redis 返回的任务创建结果无效")
    return int(raw_result[0]) == 1, _decode_state(raw_result[1])


def transition_state(
    connection,
    *,
    task_key: str,
    dedupe_key: str,
    state: Dict[str, Any],
    ttl_seconds: int,
) -> Dict[str, Any]:
    payload = _dump_state(state)
    try:
        raw_result = connection.eval(
            _TRANSITION_STATE_SCRIPT,
            2,
            task_key,
            dedupe_key,
            payload,
            int(ttl_seconds),
            str(state["task_id"]),
            str(state.get("status") or ""),
            "1" if state.get("publish_claimed") else "0",
        )
    except Exception as exc:
        raise QueryTaskCoordinationError("Redis 无法更新教务查询任务") from exc
    if not isinstance(raw_result, (list, tuple)) or len(raw_result) != 2:
        raise QueryTaskCoordinationError("Redis 返回的任务更新结果无效")
    result_code = int(raw_result[0])
    if result_code == 0:
        raise QueryTaskCoordinationError("Redis 查询任务不存在或已过期")
    if result_code < 0:
        raise QueryTaskCoordinationError("Redis 查询任务状态损坏")
    return _decode_state(raw_result[1])


def load_state(connection, task_key: str) -> Optional[Dict[str, Any]]:
    try:
        raw_value = connection.get(task_key)
    except Exception as exc:
        raise QueryTaskCoordinationError("Redis 无法读取教务查询任务") from exc
    if raw_value is None:
        return None
    return _decode_state(raw_value)
