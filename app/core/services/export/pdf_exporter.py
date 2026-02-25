# -*- coding: utf-8 -*-
"""PDF 导出生成器（WeasyPrint + Jinja2 + Pygments）"""
from __future__ import annotations

import base64
import datetime
import logging
import os
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

# Windows: 注册 MSYS2 DLL 目录，WeasyPrint 的 cffi 需要找到 GTK 库
if sys.platform == "win32":
    _msys2_bin = Path(r"C:\msys64\ucrt64\bin")
    if _msys2_bin.is_dir():
        os.add_dll_directory(str(_msys2_bin))

from jinja2 import Environment, FileSystemLoader
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, TextLexer

from app.core.utils.portable_question_format import normalize_portable_type

from .base import ExportRequest, ExportResult, build_filename
from .formatter import split_content, format_fill_blanks

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"
_ASSETS_DIR = Path(__file__).parent / "assets"
_QR_IMAGE = _ASSETS_DIR / "miniprogram_qr.jpg"


def _get_upload_dir() -> Path:
    """获取上传文件目录。"""
    try:
        from flask import current_app
        return Path(current_app.config["UPLOAD_FOLDER"])
    except Exception:
        return Path(__file__).parents[4] / "var" / "uploads"

_TYPE_ORDER = ["single_choice", "multi_choice", "boolean", "fill", "essay"]
_TYPE_LABELS = {
    "single_choice": "选择题",
    "multi_choice": "多选题",
    "boolean": "判断题",
    "fill": "填空题",
    "essay": "简答题",
}
_CN_NUMBERS = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]


def generate_pdf(req: ExportRequest, questions: list[dict[str, Any]]) -> ExportResult:
    """生成 PDF 文档并返回 ExportResult。"""
    try:
        from weasyprint import HTML
    except ImportError as e:
        raise RuntimeError(f"PDF 导出需要安装 weasyprint: {e}") from e

    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("export_pdf.html")

    # 按题型分组
    grouped = _group_by_type(questions)
    groups = []
    idx = 0
    for p_type in _TYPE_ORDER:
        items = grouped.get(p_type, [])
        if not items:
            continue
        label = _TYPE_LABELS.get(p_type, p_type)
        cn = _CN_NUMBERS[idx] if idx < len(_CN_NUMBERS) else str(idx + 1)
        rendered_items = [_render_question(q, i + 1, p_type, req.include_answer) for i, q in enumerate(items)]
        groups.append({
            "heading": f"{cn}、{label}（共 {len(items)} 题）",
            "questions": rendered_items,
        })
        idx += 1

    pygments_css = HtmlFormatter(style="friendly").get_style_defs(".highlight")
    date_str = datetime.datetime.now().strftime("%Y年%m月%d日")

    # 小程序码 base64
    qr_data_uri = ""
    if _QR_IMAGE.is_file():
        b64 = base64.b64encode(_QR_IMAGE.read_bytes()).decode()
        qr_data_uri = f"data:image/jpeg;base64,{b64}"

    html_str = template.render(
        subject_name=req.subject_name,
        date_str=date_str,
        groups=groups,
        total_count=len(questions),
        pygments_css=pygments_css,
        qr_data_uri=qr_data_uri,
    )

    buf = BytesIO()
    HTML(string=html_str).write_pdf(buf)
    buf.seek(0)

    filename = build_filename(req, "pdf")

    return ExportResult(
        buffer=buf,
        filename=filename,
        content_type="application/pdf",
    )


def _group_by_type(questions: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for q in questions:
        pt = normalize_portable_type(q.get("type", ""))
        if pt not in _TYPE_ORDER:
            pt = "essay"
        grouped.setdefault(pt, []).append(q)
    return grouped


def _highlight_code(code: str, language: str) -> str:
    try:
        lexer = get_lexer_by_name(language) if language else TextLexer()
    except Exception:
        lexer = TextLexer()
    formatter = HtmlFormatter(nowrap=False, cssclass="highlight")
    return highlight(code, lexer, formatter)


def _render_question(q: dict[str, Any], num: int, p_type: str, include_answer: bool) -> dict[str, Any]:
    """将单题渲染为模板可用的字典。"""
    content = str(q.get("content") or "")
    options = q.get("options") or []
    answer_raw = q.get("answer")
    analysis = str(q.get("analysis") or "")

    if p_type == "fill":
        content = format_fill_blanks(content)

    content_html = _segments_to_html(split_content(content))

    options_html = []
    if options and isinstance(options, list):
        for i, opt in enumerate(options):
            letter = chr(ord("A") + i) if i < 26 else str(i + 1)
            opt_text = str(opt).strip()
            if len(opt_text) > 2 and opt_text[0].isalpha() and opt_text[1] in (".", "．", "、"):
                opt_text = opt_text[2:].strip()
            options_html.append(f"{letter}. {opt_text}")

    answer_str = ""
    analysis_html = ""
    if include_answer:
        answer_str = _format_answer(answer_raw, p_type)
        if analysis:
            analysis_html = _segments_to_html(split_content(analysis))

    # 答案中的换行也转为 <br>
    from markupsafe import escape
    answer_html = str(escape(answer_str)).replace("\n", "<br>") if answer_str else ""

    # 题目图片转 base64
    image_data_uris: list[str] = []
    image_paths = q.get("image_paths") or []
    if image_paths:
        upload_dir = _get_upload_dir()
        for rel_path in image_paths:
            img_file = upload_dir / rel_path
            if not img_file.is_file():
                continue
            try:
                suffix = img_file.suffix.lower()
                mime = "image/png" if suffix == ".png" else "image/jpeg"
                b64 = base64.b64encode(img_file.read_bytes()).decode()
                image_data_uris.append(f"data:{mime};base64,{b64}")
            except Exception:
                pass

    return {
        "num": num,
        "content_html": content_html,
        "options": options_html,
        "answer": answer_str,
        "answer_html": answer_html,
        "analysis_html": analysis_html,
        "images": image_data_uris,
    }


def _segments_to_html(segments: list) -> str:
    parts: list[str] = []
    for seg in segments:
        if seg.kind == "code_block":
            parts.append(_highlight_code(seg.text, seg.language))
        elif seg.kind == "inline_code":
            from markupsafe import escape
            parts.append(f'<code class="inline-code">{escape(seg.text)}</code>')
        else:
            from markupsafe import escape
            text = str(escape(seg.text)).replace("\n", "<br>")
            parts.append(text)
    return "".join(parts)


def _format_answer(answer_raw: Any, p_type: str) -> str:
    if answer_raw is None:
        return ""
    if isinstance(answer_raw, list):
        if not answer_raw:
            return ""
        if p_type in ("single_choice", "multi_choice"):
            letters = []
            for v in answer_raw:
                try:
                    idx = int(v)
                    if 0 <= idx < 26:
                        letters.append(chr(ord("A") + idx))
                except (ValueError, TypeError):
                    pass
            return "".join(sorted(set(letters))) if letters else str(answer_raw)
        if p_type == "boolean":
            v = answer_raw[0] if answer_raw else None
            return "正确" if v is True else ("错误" if v is False else str(v))
        if p_type == "fill":
            parts = []
            for i, group in enumerate(answer_raw):
                if isinstance(group, list):
                    parts.append(f"空{i+1}: {' / '.join(str(x) for x in group)}")
                else:
                    parts.append(f"空{i+1}: {group}")
            return "；".join(parts)
        return "\n".join(str(x) for x in answer_raw)
    return str(answer_raw)
