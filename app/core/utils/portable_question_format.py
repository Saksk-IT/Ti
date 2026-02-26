# -*- coding: utf-8 -*-
"""统一题目 JSON 交换格式（Portable Question Format）

目标：把项目内不同存储/展示格式（题型中文、答案字母、填空 ';;' 等）统一映射到一套
前后端/脚本可复用的 JSON 结构：

{
  "questions": [
    {
      "id": 1001,
      "type": "single_choice|multi_choice|boolean|fill|essay",
      "content": "...",          # 填空建议用 {0}{1} 占位
      "options": ["...", "..."],
      "answer": [...],           # 统一数组：选择题用索引；判断题用 [true/false]；填空用二维数组；简答用字符串数组
      "analysis": "...",
      "tags": ["..."],
      "difficulty": 1
    }
  ],
  "meta": { ... }               # 可选
}

注意：该模块只做"导入/导出转换"，不改变数据库表结构。
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

BLANK_TOKEN = "__"
_PLACEHOLDER_RE = re.compile(r"\{(\d+)\}")
PORTABLE_TYPES = ("single_choice", "multi_choice", "boolean", "fill", "essay")


def normalize_newlines(text: Any) -> str:
    return str(text or "").replace("\r\n", "\n").replace("\r", "\n")


def normalize_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, str):
        s = tags.strip()
        if not s:
            return []
        # 兼容：tags 可能是 JSON 数组字符串（例如 "[]"/'["A","B"]'）
        if s.startswith("["):
            try:
                import json as _json

                parsed = _json.loads(s)
                if isinstance(parsed, list):
                    return [str(t).strip() for t in parsed if str(t).strip()]
            except Exception:
                pass
        raw = s.replace("，", ",")
        # 兼容：历史数据可能存了 "[]"
        out = [t.strip() for t in raw.split(",") if t.strip()]
        return [t for t in out if t not in ("[]", "[ ]")]
    if isinstance(tags, list):
        return [str(t).strip() for t in tags if str(t).strip()]
    return [str(tags).strip()] if str(tags).strip() else []


def tags_to_storage_str(tags: Any) -> str:
    cleaned = normalize_tags(tags)
    return ",".join(cleaned)


def q_type_to_portable_type(q_type: Any) -> str:
    t = str(q_type or "").strip()
    if not t:
        return "essay"
    if "多选" in t:
        return "multi_choice"
    if "选择" in t or "单选" in t:
        return "single_choice"
    if "判断" in t:
        return "boolean"
    if "填空" in t:
        return "fill"
    return "essay"


def portable_type_to_q_type(portable_type: Any, *, essay_q_type: str = "简答题") -> str:
    pt = normalize_portable_type(portable_type)
    if pt == "single_choice":
        return "选择题"
    if pt == "multi_choice":
        return "多选题"
    if pt == "boolean":
        return "判断题"
    if pt == "fill":
        return "填空题"
    return essay_q_type


def normalize_portable_type(portable_type: Any) -> str:
    v = str(portable_type or "").strip().lower()
    if not v:
        return ""
    aliases = {
        "single": "single_choice",
        "single_choice": "single_choice",
        "singlechoice": "single_choice",
        "multi": "multi_choice",
        "multiple": "multi_choice",
        "multi_choice": "multi_choice",
        "multichoice": "multi_choice",
        "boolean": "boolean",
        "bool": "boolean",
        "judge": "boolean",
        "true_false": "boolean",
        "truefalse": "boolean",
        "fill": "fill",
        "fill_in_the_blank": "fill",
        "fill-in-the-blank": "fill",
        "fillblank": "fill",
        "fill_in_the_blank_question": "fill",
        "essay": "essay",
        "short_answer": "essay",
        "shortanswer": "essay",
    }
    return aliases.get(v, v)


def any_type_to_portable_type(value: Any) -> str:
    """兼容入参既可能是中文题型，也可能已经是 PQF type。"""
    pt = normalize_portable_type(value)
    if pt in PORTABLE_TYPES:
        return pt
    return q_type_to_portable_type(value)


def fill_content_internal_to_portable(content: str) -> str:
    text = normalize_newlines(content)
    if BLANK_TOKEN not in text:
        return text
    parts = text.split(BLANK_TOKEN)
    blanks = max(0, len(parts) - 1)
    out: List[str] = []
    for i, part in enumerate(parts):
        out.append(part)
        if i < blanks:
            out.append("{" + str(i) + "}")
    return "".join(out)


def fill_content_portable_to_internal(content: str) -> Tuple[str, List[int]]:
    text = normalize_newlines(content)
    order: List[int] = []

    def _repl(m: re.Match) -> str:
        try:
            order.append(int(m.group(1)))
        except Exception:
            order.append(0)
        return BLANK_TOKEN

    new_text = _PLACEHOLDER_RE.sub(_repl, text)
    if not order:
        # 兼容：content 已经是 "__" 占位符
        blanks = new_text.count(BLANK_TOKEN)
        if blanks > 0:
            order = list(range(blanks))
    return new_text, order


def _letters_from_any(raw: Any) -> List[str]:
    s = str(raw or "")
    letters = re.findall(r"[A-Za-z]", s)
    return [c.upper() for c in letters]


def _indices_from_portable_answer(ans: Any) -> List[int]:
    if ans is None:
        return []
    if isinstance(ans, list):
        raw_list = ans
    else:
        raw_list = [ans]
    out: List[int] = []
    for v in raw_list:
        if isinstance(v, bool):
            # bool 属于 int 的子类，选择题不应该出现；这里直接跳过
            continue
        try:
            i = int(v)
        except Exception:
            continue
        if i < 0:
            continue
        out.append(i)
    # 去重并排序，保证稳定
    return sorted(set(out))


def _choice_answer_indices_to_letters(indices: List[int], *, multi: bool) -> str:
    if not indices:
        return ""
    letters = []
    for i in indices:
        if 0 <= i < 26:
            letters.append(chr(ord("A") + i))
    if not letters:
        return ""
    letters = sorted(set(letters))
    return "".join(letters) if multi else letters[0]


def _choice_answer_letters_to_indices(answer: str) -> List[int]:
    letters = re.findall(r"[A-Za-z]", str(answer or ""))
    out: List[int] = []
    for c in letters:
        u = c.upper()
        if "A" <= u <= "Z":
            out.append(ord(u) - ord("A"))
    return sorted(set(out))


def _normalize_boolean_answer_to_bool(ans: Any) -> Optional[bool]:
    # portable: [true]/[false] 或 [0]/[1]
    if isinstance(ans, bool):
        return ans
    if isinstance(ans, (int, float)) and not isinstance(ans, bool):
        return bool(int(ans) == 0)
    s = str(ans or "").strip().lower()
    if not s:
        return None
    if s in ("true", "t", "1", "yes", "y", "对", "正确", "是", "√"):
        return True
    if s in ("false", "f", "0", "no", "n", "错", "错误", "否", "×"):
        return False
    return None


def boolean_storage_to_portable(answer: Any) -> List[Any]:
    s = str(answer or "").strip()
    if not s:
        return []
    v = _normalize_boolean_answer_to_bool(s)
    if v is None:
        return []
    return [v]


def boolean_portable_to_storage(answer: Any) -> str:
    # answer 期望为 list，但也兼容单值
    if isinstance(answer, list) and answer:
        v = answer[0]
    else:
        v = answer
    b = _normalize_boolean_answer_to_bool(v)
    if b is None:
        return ""
    return "正确" if b else "错误"


def fill_storage_to_portable(answer: Any, *, blank_count: Optional[int] = None) -> List[List[str]]:
    s = normalize_newlines(answer).strip()
    if not s:
        return []
    groups = [g for g in s.split(";;")]
    out: List[List[str]] = []
    for g in groups:
        alts = [x.strip() for x in str(g or "").split(";") if x.strip()]
        out.append(alts)
    if blank_count is not None and blank_count > 0:
        while len(out) < blank_count:
            out.append([])
        if len(out) > blank_count:
            out = out[:blank_count]
    return out


def fill_portable_to_storage(answer: Any, *, content_placeholder_order: Optional[List[int]] = None) -> str:
    # answer: [[...],[...]]，索引对应 {0}{1}...；内部存储需按题干出现顺序展开
    if not isinstance(answer, list):
        return ""
    groups_by_index: List[List[str]] = []
    for g in answer:
        if isinstance(g, list):
            groups_by_index.append([str(x).strip() for x in g if str(x).strip()])
        else:
            # 兼容传了字符串：认为该空只有一个答案
            v = str(g).strip()
            groups_by_index.append([v] if v else [])

    order = content_placeholder_order or list(range(len(groups_by_index)))
    groups_in_order: List[str] = []
    for idx in order:
        g = groups_by_index[idx] if 0 <= idx < len(groups_by_index) else []
        groups_in_order.append(";".join(g))
    return ";;".join(groups_in_order).strip(";")


def portable_question_to_internal(
    item: Dict[str, Any],
    *,
    scope: str,
    essay_q_type: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """把统一 JSON 题目对象转换为内部可入库字段。

    scope:
      - "user_bank": user_bank_questions（选项存纯文本；判断题存"正确/错误"）
      - "question_center": questions（选项更推荐存带前缀的列表，便于全站兼容 parse_options）
    """
    errors: List[str] = []

    essay_qt = essay_q_type or "简答题"

    p_type = normalize_portable_type(item.get("type"))
    if not p_type:
        errors.append("缺少 type")
    q_type = portable_type_to_q_type(p_type, essay_q_type=essay_qt)

    raw_content = normalize_newlines(item.get("content")).strip()
    if not raw_content:
        errors.append("题干为空")

    options_raw = item.get("options", [])
    if isinstance(options_raw, str):
        # 允许 options 是 JSON 字符串
        try:
            import json as _json

            options_raw = _json.loads(options_raw)
        except Exception:
            options_raw = []
    options_list = [str(x) for x in (options_raw or [])] if isinstance(options_raw, list) else []

    content = raw_content
    placeholder_order: List[int] = []
    if p_type == "fill":
        content, placeholder_order = fill_content_portable_to_internal(content)

    answer_val = item.get("answer")
    answer_storage = ""
    if p_type in ("single_choice", "multi_choice"):
        idxs = _indices_from_portable_answer(answer_val)
        answer_storage = _choice_answer_indices_to_letters(idxs, multi=(p_type == "multi_choice"))
    elif p_type == "boolean":
        answer_storage = boolean_portable_to_storage(answer_val)
        if not options_list:
            options_list = ["正确", "错误"]
    elif p_type == "fill":
        answer_storage = fill_portable_to_storage(answer_val, content_placeholder_order=placeholder_order)
    else:
        # essay
        if isinstance(answer_val, list):
            answer_storage = "\n".join([normalize_newlines(x).rstrip() for x in answer_val if str(x or "").strip()]).strip()
        else:
            answer_storage = normalize_newlines(answer_val).strip()

    analysis = normalize_newlines(item.get("analysis")).strip()
    difficulty = item.get("difficulty", 1)
    try:
        difficulty = int(difficulty or 1)
    except Exception:
        difficulty = 1
    difficulty = max(1, min(5, difficulty))

    tags = normalize_tags(item.get("tags"))

    # 题库中心：为了避免 parse_options 的历史兼容问题，把纯文本 options 转成带 A. 前缀的列表
    if scope == "question_center" and p_type in ("single_choice", "multi_choice") and options_list:
        seed = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        options_list = [f"{seed[i] if i < len(seed) else str(i+1)}. {str(v)}" for i, v in enumerate(options_list)]

    return (
        {
            "q_type": q_type,
            "content": content,
            "options": options_list,
            "answer": answer_storage,
            "explanation": analysis,
            "difficulty": difficulty,
            "tags": tags,
            "portable_type": p_type,
        },
        errors,
    )


def internal_question_to_portable(
    *,
    q_id: Optional[int],
    q_type: Any,
    content: Any,
    options: Any,
    answer: Any,
    explanation: Any,
    difficulty: Any,
    tags: Any = None,
) -> Dict[str, Any]:
    p_type = q_type_to_portable_type(q_type)

    text = normalize_newlines(content).strip()
    out_content = fill_content_internal_to_portable(text) if p_type == "fill" else text

    # options 允许为 JSON 字符串/列表/None
    opts: List[str] = []
    if options:
        if isinstance(options, str):
            try:
                import json as _json

                raw = _json.loads(options)
            except Exception:
                raw = []
        else:
            raw = options
        if isinstance(raw, list):
            # 兼容历史的 "A. xxx" / dict 等
            try:
                from app.core.utils.options_parser import parse_options

                parsed = parse_options(raw)
                if parsed:
                    opts = [str(x.get("value") or "") for x in parsed]
                else:
                    opts = [str(x) for x in raw]
            except Exception:
                opts = [str(x) for x in raw]

    ans = normalize_newlines(answer).strip()
    portable_answer: Any = []
    if p_type == "single_choice":
        idxs = _choice_answer_letters_to_indices(ans)
        portable_answer = [idxs[0]] if idxs else []
    elif p_type == "multi_choice":
        portable_answer = _choice_answer_letters_to_indices(ans)
    elif p_type == "boolean":
        portable_answer = boolean_storage_to_portable(ans)
        if not opts:
            opts = ["正确", "错误"]
    elif p_type == "fill":
        blank_count = out_content.count("{")
        portable_answer = fill_storage_to_portable(ans, blank_count=blank_count if blank_count > 0 else None)
    else:
        portable_answer = [ans] if ans else []

    try:
        diff = int(difficulty or 1)
    except Exception:
        diff = 1
    diff = max(1, min(5, diff))

    return {
        "id": int(q_id) if q_id is not None else None,
        "type": p_type,
        "content": out_content,
        "options": opts,
        "answer": portable_answer,
        "analysis": normalize_newlines(explanation).strip(),
        "tags": normalize_tags(tags),
        "difficulty": diff,
    }
