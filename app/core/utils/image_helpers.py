# -*- coding: utf-8 -*-
"""图片路径工具函数（消除项目中多处重复实现）"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any


QUESTION_IMAGE_KINDS = ("content", "answer", "explanation")


def normalize_upload_relative_path(raw_val: Any) -> str:
    """将上传路径统一成相对 uploads 根目录的格式。"""
    if raw_val is None:
        return ""
    s = str(raw_val).strip()
    if not s:
        return ""
    if s.startswith("/uploads/"):
        return s[len("/uploads/"):].strip()
    if s.startswith("uploads/"):
        return s[len("uploads/"):].strip()
    return s


def _normalize_path_list(raw_val: Any) -> list[str]:
    if raw_val is None:
        return []
    if isinstance(raw_val, (list, tuple, set)):
        values = list(raw_val)
    else:
        values = [raw_val]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in values:
        path = normalize_upload_relative_path(item)
        if not path or path in seen:
            continue
        cleaned.append(path)
        seen.add(path)
    return cleaned


def normalize_question_image_groups(raw_val: Any) -> dict[str, list[str]]:
    """解析题目图片分类结构，兼容旧单路径/数组格式。"""
    groups = {kind: [] for kind in QUESTION_IMAGE_KINDS}
    if raw_val is None:
        return groups

    parsed = raw_val
    if isinstance(raw_val, str):
        s = raw_val.strip()
        if not s or s in ("[]", "[ ]", "{}", "{ }"):
            return groups
        try:
            parsed = json.loads(s)
        except Exception:
            groups["content"] = _normalize_path_list(s)
            return groups

    if isinstance(parsed, Mapping):
        groups["content"] = _normalize_path_list(
            parsed.get("content")
            or parsed.get("question")
            or parsed.get("stem")
            or parsed.get("images")
        )
        groups["answer"] = _normalize_path_list(
            parsed.get("answer") or parsed.get("answer_images")
        )
        groups["explanation"] = _normalize_path_list(
            parsed.get("explanation")
            or parsed.get("analysis")
            or parsed.get("analysis_images")
            or parsed.get("explanation_images")
        )
        return groups

    if isinstance(parsed, (list, tuple, set)):
        groups["content"] = _normalize_path_list(parsed)
        return groups

    groups["content"] = _normalize_path_list(parsed)
    return groups


def flatten_question_image_paths(raw_val: Any) -> list[str]:
    groups = normalize_question_image_groups(raw_val)
    merged: list[str] = []
    seen: set[str] = set()
    for kind in QUESTION_IMAGE_KINDS:
        for path in groups[kind]:
            if path in seen:
                continue
            merged.append(path)
            seen.add(path)
    return merged


def serialize_question_image_groups(raw_val: Any) -> str | None:
    """序列化题目图片分类结构；空值返回 None 以避免写入 '[]'。"""
    groups = normalize_question_image_groups(raw_val)
    has_content = bool(groups["content"])
    has_answer = bool(groups["answer"])
    has_explanation = bool(groups["explanation"])

    if not (has_content or has_answer or has_explanation):
        return None
    if has_content and not has_answer and not has_explanation:
        return json.dumps(groups["content"], ensure_ascii=False)
    return json.dumps(groups, ensure_ascii=False)


def normalize_image_paths(raw_val: Any) -> list[str]:
    """将 image_path 字段解析为题干图片列表，兼容新旧格式。"""
    return normalize_question_image_groups(raw_val)["content"]
