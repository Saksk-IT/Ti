# -*- coding: utf-8 -*-
"""Markdown 渲染工具（服务端）"""
from markdown_it import MarkdownIt

from .content_sanitizer import sanitize_html


def _build_markdown_renderer() -> MarkdownIt:
    """构建论坛 Markdown 渲染器。"""
    # 以 CommonMark 为基础，并显式开启表格语法（GFM 常用能力）。
    return MarkdownIt("commonmark", {"html": False, "breaks": True}).enable("table")


_MD = _build_markdown_renderer()


def render_markdown_to_safe_html(markdown_source: str) -> str:
    """将 Markdown 渲染为安全 HTML。"""
    src = (markdown_source or "").strip()
    if not src:
        return ""
    rendered = _MD.render(src)
    return sanitize_html(rendered)
