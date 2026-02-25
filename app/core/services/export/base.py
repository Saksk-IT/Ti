# -*- coding: utf-8 -*-
"""导出数据类定义"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Literal


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
