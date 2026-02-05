# -*- coding: utf-8 -*-
"""
AI 解析任务（用于 RQ worker）

注意：
- 任务函数需要可被 worker import，因此放在独立模块下（app/tasks）。
- 任务执行时不依赖 Flask current_app（避免 worker 需要 app_context）。
"""

from __future__ import annotations

import os
from typing import Any, Dict, Optional

from app.core.utils.redis_utils import get_redis_connection, get_redis_url_from_env
from app.modules.quiz.services.ai_explain_service import generate_ai_explain


def _placeholder_explain() -> Dict[str, Any]:
    tip = '（未配置 DASHSCOPE_API_KEY，当前为模板解析；配置后将自动使用百炼模型）'
    lines = [
        tip,
        '',
        '建议解题思路：',
        '1) 先圈出关键词与限定条件。',
        '2) 把题干转为可验证的结论/公式/步骤。',
        '3) 对选择题：用排除法 + 代入验证。',
        '4) 对填空/简答题：列步骤，逐步推导，最后回代检查。',
    ]
    return {'provider': 'placeholder', 'explain': '\n'.join(lines)}


def ai_explain_task(
    *,
    payload: Dict[str, Any],
    model: Optional[str] = None,
    timeout: int = 25,
    cache_key: Optional[str] = None,
    cache_ttl_seconds: int = 30 * 24 * 60 * 60,
) -> Dict[str, Any]:
    """生成 AI 解析（任务侧）。"""
    api_key = (os.environ.get('DASHSCOPE_API_KEY') or '').strip()
    base_url = (os.environ.get('DASHSCOPE_BASE_URL') or 'https://dashscope.aliyuncs.com/compatible-mode/v1').strip()
    mdl = (model or os.environ.get('DASHSCOPE_MODEL') or 'qwen-plus').strip() or 'qwen-plus'

    if not api_key:
        result = _placeholder_explain()
    else:
        explain = generate_ai_explain(
            api_key=api_key,
            base_url=base_url,
            model=mdl,
            payload=payload or {},
            timeout=int(timeout or 25),
        )
        result = {'provider': 'dashscope', 'model': mdl, 'explain': explain}

    # 写入 Redis 缓存（可选）
    if cache_key:
        conn = get_redis_connection(get_redis_url_from_env())
        if conn is not None:
            try:
                import json

                conn.set(cache_key, json.dumps(result, ensure_ascii=False), ex=int(cache_ttl_seconds))
            except Exception:
                pass

    return result
