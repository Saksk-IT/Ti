# -*- coding: utf-8 -*-
"""Markdown 渲染工具（服务端）"""
from markdown_it import MarkdownIt

from .content_sanitizer import sanitize_html


_MD = MarkdownIt("commonmark", {"html": False, "breaks": True})


def render_markdown_to_safe_html(markdown_source: str) -> str:
    """将 Markdown 渲染为安全 HTML。"""
    src = (markdown_source or "").strip()
    if not src:
        return ""
    rendered = _MD.render(src)
    return sanitize_html(rendered)
