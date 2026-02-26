# -*- coding: utf-8 -*-
"""AI 评分服务 — 主观题（简答/论述）自动评分

复用 DashScope 客户端，调用 LLM 判断用户答案是否正确。
解析失败时返回 None（降级为 auto_full 模式）。
"""
from __future__ import annotations

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def _get_client():
    """延迟获取 DashScope 客户端（避免循环导入 + 读取运行时配置）"""
    from flask import current_app
    from app.modules.quiz.services.dashscope_client import DashScopeClient

    api_key = current_app.config.get('DASHSCOPE_API_KEY', '')
    base_url = current_app.config.get('DASHSCOPE_BASE_URL', '')
    return DashScopeClient(api_key=api_key, base_url=base_url)


def grade_essay_answer(
    question_content: str,
    standard_answer: str,
    user_answer: str,
) -> Optional[int]:
    """调用 AI 评分主观题答案。

    Returns:
        1 = 正确, 0 = 错误, None = 评分失败（降级）
    """
    if not user_answer or not user_answer.strip():
        return 0

    system_prompt = (
        "你是一个考试阅卷助手。根据题目内容和标准答案，判断学生的回答是否正确。\n"
        "只需返回一个 JSON 对象：{\"correct\": true} 或 {\"correct\": false}。\n"
        "不要输出任何其他内容。\n"
        "评判标准：意思相近即可，不要求完全一致。"
    )

    user_prompt = (
        f"【题目】{question_content}\n"
        f"【标准答案】{standard_answer}\n"
        f"【学生回答】{user_answer}"
    )

    try:
        from flask import current_app
        client = _get_client()
        model = current_app.config.get('DASHSCOPE_MODEL', 'qwen-turbo')

        response_text = client.chat_completions(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=50,
            timeout=15,
        )

        # 解析 JSON 响应
        result = json.loads(response_text.strip())
        if isinstance(result, dict) and 'correct' in result:
            return 1 if result['correct'] else 0

        logger.warning("AI 评分返回格式异常: %s", response_text)
        return None

    except Exception as e:
        logger.warning("AI 评分失败，降级为 auto_full: %s", e)
        return None
