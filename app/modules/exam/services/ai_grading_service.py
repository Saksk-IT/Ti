# -*- coding: utf-8 -*-
"""AI 评分服务 — 主观题（简答/论述）自动评分

复用 DashScope 客户端，调用 LLM 对学生答案进行评分。
返回 score(0-100)、is_correct(bool)、feedback(评语)。
解析失败时返回 None（降级为 auto_full 模式）。
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# 60 分及以上视为"正确"
_PASS_THRESHOLD = 60


@dataclass(frozen=True)
class GradingResult:
    """AI 判分结果"""
    score: int           # 0-100
    is_correct: bool     # score >= _PASS_THRESHOLD
    feedback: str        # 详细评语


def _get_ai_cfg() -> dict:
    """获取 AI 配置（DB 优先、.env fallback）"""
    from app.modules.admin.services.system_config_service import SystemConfigService
    return SystemConfigService.get_ai_config()


def _get_client():
    """延迟获取 AI 客户端（避免循环导入 + 读取运行时配置）"""
    from app.modules.quiz.services.ai_client import AIClient
    cfg = _get_ai_cfg()
    return AIClient(
        api_key=cfg['api_key'],
        base_url=cfg['base_url'],
        api_type=cfg.get('api_type') or 'chat_completions',
        provider=cfg.get('provider') or 'custom',
    )


_SYSTEM_PROMPT = """\
你是一位专业的考试阅卷老师。请根据题目、标准答案和学生回答进行评分。

## 评分标准（适中）
- 核心要点必须覆盖，但表述可以灵活，不要求与标准答案措辞完全一致
- 意思正确、逻辑通顺即可得分
- 如果标准答案包含多个要点，按要点覆盖比例给分
- 有额外正确补充不扣分，但错误内容要适当扣分
- 完全空白或完全无关的回答给 0 分

## 输出格式
严格返回以下 JSON，不要输出任何其他内容：
{"score": <0-100整数>, "feedback": "<评语>"}

## 评语要求
- 用中文，简洁明了，2-4 句话
- 先肯定答对的部分，再指出不足
- 如果满分，简短表扬即可
- 如果 0 分，指出答案与题目的偏差\
"""


def _parse_ai_response(text: str) -> Optional[dict]:
    """从 AI 响应中提取 JSON，兼容 markdown code block 包裹"""
    if not text:
        return None

    cleaned = text.strip()
    # 去除 ```json ... ``` 包裹
    md_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', cleaned, re.DOTALL)
    if md_match:
        cleaned = md_match.group(1)

    # 尝试直接解析
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict) and 'score' in obj:
            return obj
    except json.JSONDecodeError:
        pass

    # 兜底：从文本中提取第一个 JSON 对象
    json_match = re.search(r'\{[^{}]*"score"\s*:\s*\d+[^{}]*\}', cleaned)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass

    return None


def grade_essay_answer(
    question_content: str,
    standard_answer: str,
    user_answer: str,
) -> Optional[GradingResult]:
    """调用 AI 评分主观题答案。

    Returns:
        GradingResult 或 None（评分失败，降级）
    """
    if not user_answer or not user_answer.strip():
        return GradingResult(score=0, is_correct=False, feedback='未作答')

    user_prompt = (
        f"【题目】\n{question_content}\n\n"
        f"【标准答案】\n{standard_answer}\n\n"
        f"【学生回答】\n{user_answer}"
    )

    try:
        client = _get_client()
        cfg = _get_ai_cfg()

        response_text = client.generate_text(
            model=cfg['model'],
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=300,
            timeout=min(cfg['timeout'], 20),
        )

        parsed = _parse_ai_response(response_text)
        if parsed is None:
            logger.warning("AI 评分返回格式异常: %s", response_text[:200])
            return None

        raw_score = parsed.get('score')
        if raw_score is None or not isinstance(raw_score, (int, float)):
            logger.warning("AI 评分缺少 score 字段: %s", parsed)
            return None

        score = max(0, min(100, int(raw_score)))
        feedback = str(parsed.get('feedback', '') or '').strip() or '评分完成'

        return GradingResult(
            score=score,
            is_correct=score >= _PASS_THRESHOLD,
            feedback=feedback,
        )

    except Exception as e:
        logger.warning("AI 评分失败，降级为 auto_full: %s", e)
        return None
