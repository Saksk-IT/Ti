# -*- coding: utf-8 -*-
"""富文本内容净化（防 XSS）"""
import re


# 允许的 HTML 标签及其属性
_ALLOWED_TAGS: dict[str, set[str]] = {
    'p': set(), 'br': set(), 'strong': set(), 'b': set(), 'em': set(), 'i': set(),
    'u': set(), 's': set(), 'blockquote': set(), 'code': set(), 'pre': set(),
    'ul': set(), 'ol': set(), 'li': set(),
    'h1': set(), 'h2': set(), 'h3': set(), 'h4': set(),
    'a': {'href', 'title', 'target', 'rel'},
    'img': {'src', 'alt', 'width', 'height'},
    'span': {'class'},
    'div': {'class'},
}

_TAG_RE = re.compile(r'<(/?)(\w+)([^>]*)(/?)>', re.DOTALL)
_ATTR_RE = re.compile(r'(\w[\w-]*)=(?:"([^"]*)"|\'([^\']*)\')')
_SCRIPT_RE = re.compile(r'<script[\s\S]*?</script>', re.IGNORECASE)
_STYLE_TAG_RE = re.compile(r'<style[\s\S]*?</style>', re.IGNORECASE)
_EVENT_RE = re.compile(r'\bon\w+\s*=', re.IGNORECASE)
_JS_URL_RE = re.compile(r'javascript\s*:', re.IGNORECASE)


def sanitize_html(html: str) -> str:
    """净化 HTML 内容，只保留安全标签和属性"""
    if not html:
        return ''

    # 移除 script / style 标签
    result = _SCRIPT_RE.sub('', html)
    result = _STYLE_TAG_RE.sub('', result)
    # 移除事件属性
    result = _EVENT_RE.sub('', result)

    def _replace_tag(m: re.Match) -> str:
        closing = m.group(1)
        tag = m.group(2).lower()
        attrs_str = m.group(3)
        self_closing = m.group(4)

        if tag not in _ALLOWED_TAGS:
            return ''

        if closing:
            return f'</{tag}>'

        allowed_attrs = _ALLOWED_TAGS[tag]
        safe_attrs: list[str] = []
        for am in _ATTR_RE.finditer(attrs_str):
            attr_name = am.group(1).lower()
            attr_val = am.group(2) if am.group(2) is not None else am.group(3)
            if attr_name not in allowed_attrs:
                continue
            if _JS_URL_RE.search(attr_val or ''):
                continue
            safe_attrs.append(f'{attr_name}="{attr_val}"')

        attrs_out = (' ' + ' '.join(safe_attrs)) if safe_attrs else ''
        sc = ' /' if self_closing or tag in ('br', 'img') else ''
        return f'<{tag}{attrs_out}{sc}>'

    return _TAG_RE.sub(_replace_tag, result)
