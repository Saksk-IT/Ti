# -*- coding: utf-8 -*-
"""统一的题目选项解析工具

背景：题库 options 字段历史上存在多种格式：
- ["A、内容", "B、内容" ...]
- ["A.内容", "B.内容" ...]
- ["内容1", "内容2" ...]（无 A/B 前缀）
- [0.4, 0.45, ...]（数字）
- [{"key": "A", "value": "内容"}, ...]（已结构化）

本模块提供统一解析函数，供 quiz 页面与 chat 题目卡片复用，避免兼容性分裂。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional


_EXPLICIT_PREFIX_RE = re.compile(r"^([A-Za-z]|\d{1,2})\s*([、.．:：])\s*(.+)$")
_ALPHA_SEED = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _parse_explicit_prefix(text: str) -> Optional[Dict[str, str]]:
    match = _EXPLICIT_PREFIX_RE.match(text)
    if not match:
        return None

    raw_key = match.group(1).strip()
    delimiter = match.group(2)
    value = match.group(3).strip()
    if not raw_key or not value:
        return None

    # 0.4 / 1.25 这类数值选项不是 "1. xxx" 前缀。
    if raw_key.isdigit() and delimiter in ('.', '．') and value[:1].isdigit():
        return None

    key = raw_key[:1].upper()
    return {'key': key, 'value': value}


def _compact_alpha_key(text: str) -> Optional[str]:
    first = text[:1].upper()
    second = text[1:2]
    if not first or first not in _ALPHA_SEED or not second:
        return None
    if second.isascii() and second.isalnum():
        return None
    return first


def _compact_digit_key(text: str) -> Optional[str]:
    first = text[:1]
    second = text[1:2]
    if not first.isdigit() or not second:
        return None
    # 只兼容 "1正确/2错误" 这类中文紧凑前缀，避免把 "1+1=2" 当选项标号。
    if not ('\u3400' <= second <= '\u9fff'):
        return None
    return first


def _is_sequential(keys: List[str], seed: str) -> bool:
    if not keys:
        return False
    expected = list(seed[:len(keys)])
    return keys == expected


def _compact_prefix_keys(texts: List[str]) -> Dict[int, str]:
    keyed_indexes = [(i, text) for i, text in enumerate(texts) if text]
    if not keyed_indexes:
        return {}

    alpha_keys = [_compact_alpha_key(text) for _, text in keyed_indexes]
    if all(alpha_keys) and _is_sequential([str(k) for k in alpha_keys], _ALPHA_SEED):
        return {idx: str(key) for (idx, _), key in zip(keyed_indexes, alpha_keys)}

    digit_keys = [_compact_digit_key(text) for _, text in keyed_indexes]
    if all(digit_keys) and _is_sequential([str(k) for k in digit_keys], "123456789"):
        return {idx: str(key) for (idx, _), key in zip(keyed_indexes, digit_keys)}

    return {}


def parse_options(raw_options: Any) -> List[Dict[str, str]]:
    """解析题目选项为统一结构：[{key, value}, ...]

    raw_options:
      - None / ''
      - JSON 字符串（DB 中常见）
      - list（部分调用方已 json.loads）

    解析策略：
      1) 若为 dict 结构，读 key/value
      2) 若为 str：优先解析 A、 / A. 前缀；否则作为纯文本，后续补 A/B/C...
      3) 其它类型（数字等）转 str
      4) 若所有 key 为空，按顺序补 A/B/C...
    """

    if raw_options is None:
        return []

    opt_list = None

    # 允许传入 JSON 字符串
    if isinstance(raw_options, str):
        s = raw_options.strip()
        if not s:
            return []
        try:
            opt_list = json.loads(s)
        except Exception:
            # 非 JSON：当作单个选项文本（极少见）
            opt_list = [s]
    else:
        opt_list = raw_options

    if not isinstance(opt_list, list):
        return []

    text_items: List[Optional[str]] = []
    for item in opt_list:
        if isinstance(item, dict):
            # 保留 value 中的换行符，只去掉首尾空白（空格、制表符），但保留换行符
            value = str(item.get('value') or '')
            # 去掉首尾的空白字符（空格、制表符），但保留换行符
            value = value.rstrip(' \t').lstrip(' \t') if value else ''
            text_items.append(None)
        else:
            item_str = '' if item is None else str(item)
            text_items.append(item_str.strip())

    compact_keys = _compact_prefix_keys([s or '' for s in text_items])

    options_payload: List[Dict[str, str]] = []
    for idx, item in enumerate(opt_list):
        if isinstance(item, dict):
            value = str(item.get('value') or '')
            value = value.rstrip(' \t').lstrip(' \t') if value else ''
            options_payload.append({
                'key': str(item.get('key') or '').strip(),
                'value': value,
            })
            continue

        # 其它类型统一转字符串
        s = text_items[idx] or ''
        if not s:
            options_payload.append({'key': '', 'value': ''})
            continue

        # 优先解析 "A、xxx" / "A.xxx" / "A：xxx" / "1. xxx"
        parsed = _parse_explicit_prefix(s)
        if parsed:
            options_payload.append(parsed)
            continue

        # 兜底兼容历史紧凑格式：仅当整组选项连续呈现 A/B/C... 或 1/2/3... 时才剥首字符。
        compact_key = compact_keys.get(idx)
        if compact_key:
            options_payload.append({
                'key': compact_key,
                'value': s[1:].lstrip(' :：.,、\t\r\n').strip(),
            })
        else:
            options_payload.append({'key': '', 'value': s})

    # 如果 key 全为空，则补 A/B/C...
    if options_payload and all((not (x.get('key') or '').strip()) for x in options_payload):
        seed = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        for i, x in enumerate(options_payload):
            x['key'] = seed[i] if i < len(seed) else str(i + 1)

    return options_payload
