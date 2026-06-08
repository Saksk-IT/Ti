# -*- coding: utf-8 -*-
from typing import Dict, List

from .ai_client import AIClient


class DashScopeClient:
    """DashScope OpenAI-compatible client (chat.completions)."""

    def __init__(self, api_key: str, base_url: str):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")

    def chat_completions(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 800,
        timeout: int = 25,
    ) -> str:
        client = AIClient(
            api_key=self.api_key,
            base_url=self.base_url,
            api_type="chat_completions",
            provider="dashscope",
        )
        return client.generate_text(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            timeout=timeout,
        )
