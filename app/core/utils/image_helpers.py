# -*- coding: utf-8 -*-
"""图片路径工具函数（消除项目中多处重复实现）"""

import json
from typing import Any


def normalize_image_paths(raw_val: Any) -> list[str]:
    """将 image_path 字段解析为相对路径列表。兼容 JSON 字符串、列表、单路径字符串。"""
    if raw_val is None:
        return []
    if isinstance(raw_val, list):
        return [str(x).strip() for x in raw_val if str(x).strip()]
    s = str(raw_val or '').strip()
    if not s or s in ('[]', '[ ]'):
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x).strip() for x in parsed if str(x).strip()]
    except Exception:
        pass
    return [s]
