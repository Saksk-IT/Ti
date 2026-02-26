# -*- coding: utf-8 -*-
"""Word(.docx) 文本提取工具

目标：尽量把 Word 内容还原成"可被文本解析器识别"的纯文本，保留换行/缩进，
并尽可能重建列表编号（1./A./a./I./•），以兼容题号与选项的识别。

注意：
- Word 的编号/项目符号通常不在 paragraph.text 中，需要从 numbering.xml 重建。
- 这里的实现以"题库导入"常见格式为优先，不追求覆盖全部 Word 排版特性。
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple, Union

from docx import Document
from docx.oxml.ns import qn
from docx.oxml.table import CT_Tbl
from docx.oxml.text.paragraph import CT_P
from docx.table import Table
from docx.text.paragraph import Paragraph


_NS = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}


@dataclass(frozen=True)
class _LevelDef:
    num_fmt: str
    lvl_text: str
    start: int


def extract_docx_text(file_bytes: bytes) -> str:
    """提取 docx 为纯文本（含换行），用于前端进一步解析。"""
    if not file_bytes:
        return ''

    doc = Document(io.BytesIO(file_bytes))
    num_to_abs, abs_defs = _parse_numbering(doc)
    counters: Dict[int, Dict[int, int]] = {}

    lines: list[str] = []
    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            line = _paragraph_to_line(block, num_to_abs, abs_defs, counters)
            lines.append(line)
            continue
        if isinstance(block, Table):
            lines.extend(_table_to_lines(block))
            continue

    text = '\n'.join(lines)
    return text.replace('\u00A0', ' ')


def _iter_block_items(parent) -> Iterable[Union[Paragraph, Table]]:
    """按文档顺序迭代段落与表格。"""
    body = parent.element.body
    for child in body.iterchildren():
        if isinstance(child, CT_P):
            yield Paragraph(child, parent)
        elif isinstance(child, CT_Tbl):
            yield Table(child, parent)


def _table_to_lines(table: Table) -> list[str]:
    lines: list[str] = []
    try:
        for row in table.rows:
            cells = []
            for cell in row.cells:
                cell_text = (cell.text or '').replace('\r\n', '\n').replace('\r', '\n')
                cells.append(cell_text)
            lines.append('\t'.join(cells))
    except Exception:
        return []
    return lines


def _paragraph_to_line(
    p: Paragraph,
    num_to_abs: Dict[int, int],
    abs_defs: Dict[int, Dict[int, _LevelDef]],
    counters: Dict[int, Dict[int, int]],
) -> str:
    prefix = _get_list_prefix(p, num_to_abs, abs_defs, counters)
    text = p.text or ''
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    if not prefix:
        return text
    if not text:
        return prefix.rstrip()
    return f'{prefix}{text}'


def _get_list_prefix(
    p: Paragraph,
    num_to_abs: Dict[int, int],
    abs_defs: Dict[int, Dict[int, _LevelDef]],
    counters: Dict[int, Dict[int, int]],
) -> str:
    info = _get_paragraph_num_info(p)
    if not info:
        return ''
    num_id, ilvl = info

    abs_id = num_to_abs.get(num_id)
    if abs_id is None:
        return ''
    lvl_def = abs_defs.get(abs_id, {}).get(ilvl)
    if not lvl_def:
        return ''

    local = counters.setdefault(num_id, {})
    for key in list(local.keys()):
        if key > ilvl:
            del local[key]

    current = local.get(ilvl)
    if current is None:
        current = max(0, int(lvl_def.start) - 1)
    current += 1
    local[ilvl] = current

    raw_text = lvl_def.lvl_text or '%1.'
    if lvl_def.num_fmt == 'bullet' and '%' not in raw_text:
        label = raw_text
    else:
        label = re.sub(r'%(\d+)', lambda m: _resolve_placeholder(m, abs_id, local, abs_defs, lvl_def), raw_text)

    if label and not label.endswith(' '):
        label += ' '
    indent = '  ' * max(0, ilvl)
    return indent + label


def _resolve_placeholder(m, abs_id: int, local: Dict[int, int], abs_defs: Dict[int, Dict[int, _LevelDef]], fallback: _LevelDef) -> str:
    try:
        idx = int(m.group(1)) - 1
    except Exception:
        idx = 0

    d = abs_defs.get(abs_id, {}).get(idx) or fallback
    val = local.get(idx)
    if val is None:
        val = max(1, int(d.start or 1))
        local[idx] = val
    return _format_number(val, d.num_fmt)


def _format_number(value: int, fmt: str) -> str:
    v = int(value or 0)
    f = (fmt or 'decimal').lower()
    if f == 'decimal':
        return str(v)
    if f == 'upperletter':
        return _alpha(v, upper=True)
    if f == 'lowerletter':
        return _alpha(v, upper=False)
    if f == 'upperroman':
        return _roman(v).upper()
    if f == 'lowerroman':
        return _roman(v).lower()
    if f == 'bullet':
        return '•'
    return str(v)


def _alpha(value: int, upper: bool) -> str:
    if value <= 0:
        return 'A' if upper else 'a'
    base = 65 if upper else 97
    n = value
    out = ''
    while n > 0:
        n -= 1
        out = chr(base + (n % 26)) + out
        n //= 26
    return out


def _roman(value: int) -> str:
    if value <= 0:
        return 'I'
    val = int(value)
    mapping = [
        (1000, 'M'),
        (900, 'CM'),
        (500, 'D'),
        (400, 'CD'),
        (100, 'C'),
        (90, 'XC'),
        (50, 'L'),
        (40, 'XL'),
        (10, 'X'),
        (9, 'IX'),
        (5, 'V'),
        (4, 'IV'),
        (1, 'I'),
    ]
    out = []
    for num, sym in mapping:
        while val >= num:
            out.append(sym)
            val -= num
    return ''.join(out) or 'I'


def _get_paragraph_num_info(p: Paragraph) -> Optional[Tuple[int, int]]:
    try:
        p_pr = p._p.pPr
        if p_pr is not None and p_pr.numPr is not None:
            num_pr = p_pr.numPr
            if num_pr.numId is not None:
                num_id = int(num_pr.numId.val)
                ilvl = int(num_pr.ilvl.val) if num_pr.ilvl is not None else 0
                return num_id, ilvl

        style = getattr(p, 'style', None)
        info = _get_style_num_info(style)
        if info:
            return info
    except Exception:
        return None
    return None


def _get_style_num_info(style) -> Optional[Tuple[int, int]]:
    current = style
    for _ in range(12):
        if current is None:
            return None
        try:
            p_pr = current._element.pPr
            if p_pr is not None and p_pr.numPr is not None:
                num_pr = p_pr.numPr
                if num_pr.numId is not None:
                    ilvl = int(num_pr.ilvl.val) if num_pr.ilvl is not None else 0
                    return int(num_pr.numId.val), ilvl
        except Exception:
            pass
        try:
            current = current.base_style
        except Exception:
            return None
    return None


def _parse_numbering(doc) -> Tuple[Dict[int, int], Dict[int, Dict[int, _LevelDef]]]:
    """读取 numbering.xml，构建 numId -> abstractNumId 与 abstractNum 的层级定义。"""
    num_to_abs: Dict[int, int] = {}
    abs_defs: Dict[int, Dict[int, _LevelDef]] = {}

    try:
        numbering = doc.part.numbering_part.element
    except Exception:
        return num_to_abs, abs_defs

    for num in numbering.findall('w:num', _NS):
        try:
            num_id = int(num.get(qn('w:numId')))
            abs_id_el = num.find('w:abstractNumId', _NS)
            if abs_id_el is None:
                continue
            abs_id = int(abs_id_el.get(qn('w:val')))
            num_to_abs[num_id] = abs_id
        except Exception:
            continue

    for abs_num in numbering.findall('w:abstractNum', _NS):
        try:
            abs_id = int(abs_num.get(qn('w:abstractNumId')))
        except Exception:
            continue

        levels: Dict[int, _LevelDef] = {}
        for lvl in abs_num.findall('w:lvl', _NS):
            try:
                ilvl = int(lvl.get(qn('w:ilvl')))
            except Exception:
                continue

            num_fmt = 'decimal'
            lvl_text = '%1.'
            start = 1

            try:
                num_fmt_el = lvl.find('w:numFmt', _NS)
                if num_fmt_el is not None and num_fmt_el.get(qn('w:val')):
                    num_fmt = str(num_fmt_el.get(qn('w:val')))
            except Exception:
                num_fmt = 'decimal'

            try:
                lvl_text_el = lvl.find('w:lvlText', _NS)
                if lvl_text_el is not None and lvl_text_el.get(qn('w:val')):
                    lvl_text = str(lvl_text_el.get(qn('w:val')))
            except Exception:
                lvl_text = '%1.'

            try:
                start_el = lvl.find('w:start', _NS)
                if start_el is not None and start_el.get(qn('w:val')):
                    start = int(start_el.get(qn('w:val')))
            except Exception:
                start = 1

            levels[ilvl] = _LevelDef(num_fmt=num_fmt, lvl_text=lvl_text, start=start)

        if levels:
            abs_defs[abs_id] = levels

    return num_to_abs, abs_defs
