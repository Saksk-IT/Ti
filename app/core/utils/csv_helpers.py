# -*- coding: utf-8 -*-
"""CSV 工具函数（消除项目中多处重复实现）"""

from typing import Any


def csv_escape(s: Any) -> str:
    """对 CSV 字段值进行转义，处理逗号、引号和换行符。"""
    s = '' if s is None else str(s)
    if any(c in s for c in [',', '"', '\n', '\r']):
        s = '"' + s.replace('"', '""') + '"'
    return s
