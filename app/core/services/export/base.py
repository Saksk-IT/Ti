# -*- coding: utf-8 -*-
"""导出数据类定义"""
from __future__ import annotations

import datetime
from dataclasses import dataclass
from io import BytesIO
from typing import Literal

_SCOPE_LABELS = {"all": "全部", "favorites": "收藏", "mistakes": "错题"}


@dataclass(frozen=True)
class ExportRequest:
    subject_id: int
    subject_name: str
    format: Literal["word", "pdf"]
    scope: Literal["all", "favorites", "mistakes"]
    q_type: str          # "all" 或具体题型
    tag: str             # "all" 或具体标签名
    include_answer: bool
    user_id: int | None


@dataclass(frozen=True)
class ExportResult:
    buffer: BytesIO
    filename: str
    content_type: str


def build_filename(req: ExportRequest, ext: str) -> str:
    """生成描述性文件名：科目_范围_题型_标签_答案模式_日期.ext"""
    parts = [req.subject_name]

    scope_label = _SCOPE_LABELS.get(req.scope, req.scope)
    if req.scope != "all":
        parts.append(scope_label)

    if req.q_type and req.q_type != "all":
        parts.append(req.q_type)

    if req.tag and req.tag != "all":
        parts.append(req.tag)

    parts.append("含答案" if req.include_answer else "仅题目")
    parts.append(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))

    name = "_".join(parts)
    # 清理文件名中的非法字符
    for ch in r'<>:"/\|?*':
        name = name.replace(ch, "_")
    return f"{name}.{ext}"
