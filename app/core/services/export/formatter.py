# -*- coding: utf-8 -*-
"""内容格式化：代码块检测、内容段拆分"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ContentSegment:
    kind: Literal["text", "code_block", "inline_code"]
    text: str
    language: str = ""


_CODE_BLOCK_RE = re.compile(
    r"```(\w*)\s*\n(.*?)```",
    re.DOTALL,
)


def split_content(raw: str) -> list[ContentSegment]:
    """将题干/解析文本拆分为普通文本段 + 代码块段。"""
    if not raw:
        return []

    segments: list[ContentSegment] = []
    last_end = 0

    for m in _CODE_BLOCK_RE.finditer(raw):
        # 代码块之前的文本
        before = raw[last_end:m.start()]
        if before.strip():
            segments.extend(_split_inline_code(before))
        lang = m.group(1) or ""
        code = m.group(2).rstrip("\n")
        segments.append(ContentSegment(kind="code_block", text=code, language=lang))
        last_end = m.end()

    # 剩余文本
    tail = raw[last_end:]
    if tail.strip():
        segments.extend(_split_inline_code(tail))

    return segments if segments else [ContentSegment(kind="text", text=raw)]


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")

_CIRCLED_NUMBERS = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]


def format_fill_blanks(content: str) -> str:
    """将填空题题干中的 __ 占位符转换为带编号的可读空位。

    例: '中国的首都是__，面积约__万' → '中国的首都是 ______① ，面积约 ______② 万'
    """
    if "__" not in content:
        return content
    parts = content.split("__")
    if len(parts) <= 1:
        return content
    result = [parts[0]]
    for i, part in enumerate(parts[1:]):
        num = _CIRCLED_NUMBERS[i] if i < len(_CIRCLED_NUMBERS) else f"({i + 1})"
        result.append(f" ______{num} ")
        result.append(part)
    return "".join(result)


def _split_inline_code(text: str) -> list[ContentSegment]:
    """拆分行内代码。"""
    parts: list[ContentSegment] = []
    last = 0
    for m in _INLINE_CODE_RE.finditer(text):
        before = text[last:m.start()]
        if before:
            parts.append(ContentSegment(kind="text", text=before))
        parts.append(ContentSegment(kind="inline_code", text=m.group(1)))
        last = m.end()
    tail = text[last:]
    if tail:
        parts.append(ContentSegment(kind="text", text=tail))
    return parts
