# -*- coding: utf-8 -*-
"""SQL 工具函数"""
from __future__ import annotations


def escape_like(value: str, escape_char: str = "\\") -> str:
    """转义 LIKE 通配符，防止用户输入 % 或 _ 导致意外匹配。

    Args:
        value: 用户输入的搜索关键词
        escape_char: ESCAPE 字符（默认反斜杠）

    Returns:
        转义后的字符串，需配合 ``ESCAPE '\\\\'`` 使用
    """
    return (
        value
        .replace(escape_char, escape_char + escape_char)
        .replace("%", escape_char + "%")
        .replace("_", escape_char + "_")
    )
