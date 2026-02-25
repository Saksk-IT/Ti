# -*- coding: utf-8 -*-
"""JSON 安全加载工具函数（消除项目中 30+ 处重复实现）"""

import json
from typing import Any


def safe_json_load(raw: Any, default: Any = None) -> Any:
    """安全解析 JSON 字符串，失败返回 default。兼容已解析的 Python 对象。"""
    if raw is None:
        return default
    if isinstance(raw, (list, dict, bool, int, float)):
        return raw
    s = str(raw).strip()
    if not s:
        return default
    try:
        return json.loads(s)
    except Exception:
        return default


def safe_load(raw: Any, default: Any = None) -> Any:
    """safe_json_load 的别名，兼容旧调用点。"""
    return safe_json_load(raw, default)
