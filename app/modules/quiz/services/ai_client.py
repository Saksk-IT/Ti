# -*- coding: utf-8 -*-
"""通用 AI 文本客户端。

支持 OpenAI-compatible Chat Completions 与 OpenAI Responses 两类接口。
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import requests


class AIClient:
    """面向应用调用层的通用文本生成客户端。"""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        api_type: str = "chat_completions",
        provider: str = "custom",
    ):
        self.api_key = (api_key or "").strip()
        self.base_url = (base_url or "").rstrip("/")
        self.api_type = (api_type or "chat_completions").strip().lower()
        self.provider = (provider or "custom").strip().lower()

    def generate_text(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 800,
        timeout: int = 25,
    ) -> str:
        if self.api_type == "responses":
            return self._responses_create(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        return self._chat_completions(
            model=model,
            messages=messages,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            timeout=timeout,
        )

    def list_models(self, *, timeout: int = 25) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("AI_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("AI_BASE_URL 未配置")

        resp = requests.get(
            f"{self.base_url}/models",
            headers=self._headers(),
            timeout=timeout,
        )
        data = self._json_or_raise(resp, "模型列表拉取失败")
        items = data.get("data") if isinstance(data, dict) else None
        if not isinstance(items, list):
            raise RuntimeError("上游未返回有效模型列表")
        models: List[Dict[str, Any]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model_id = str(item.get("id") or "").strip()
            if not model_id:
                continue
            models.append({
                "id": model_id,
                "owned_by": item.get("owned_by") or item.get("owner") or "",
            })
        return models

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _chat_completions(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        timeout: int,
    ) -> str:
        if not self.api_key:
            raise ValueError("AI_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("AI_BASE_URL 未配置")

        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
        }
        data = self._post_json(
            f"{self.base_url}/chat/completions",
            payload,
            timeout,
            "AI Chat Completions 调用失败",
        )

        try:
            choices = data.get("choices") or []
            msg = (choices[0] or {}).get("message") or {}
            content = (msg.get("content") or "").strip()
        except Exception:
            content = ""
        if not content:
            raise RuntimeError("AI 未返回有效内容")
        return content

    def _responses_create(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        timeout: int,
    ) -> str:
        if not self.api_key:
            raise ValueError("AI_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("AI_BASE_URL 未配置")

        payload: Dict[str, Any] = {
            "model": model,
            "input": [
                {
                    "role": str(msg.get("role") or "user"),
                    "content": str(msg.get("content") or ""),
                }
                for msg in messages
            ],
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_output_tokens": int(max_tokens),
        }
        data = self._post_json(
            f"{self.base_url}/responses",
            payload,
            timeout,
            "AI Responses 调用失败",
        )
        content = self._extract_responses_text(data)
        if not content:
            raise RuntimeError("AI Responses 未返回有效内容")
        return content

    def _post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: int,
        error_prefix: str,
    ) -> Dict[str, Any]:
        resp = requests.post(url, headers=self._headers(), json=payload, timeout=timeout)
        return self._json_or_raise(resp, error_prefix)

    @staticmethod
    def _json_or_raise(resp: requests.Response, error_prefix: str) -> Dict[str, Any]:
        if resp.status_code < 200 or resp.status_code >= 300:
            msg = ""
            try:
                js = resp.json()
                msg = js.get("error", {}).get("message") or js.get("message") or ""
            except Exception:
                msg = resp.text[:300] if resp.text else ""
            raise RuntimeError(f"{error_prefix}：HTTP {resp.status_code} {msg}".strip())

        try:
            data = resp.json()
        except json.JSONDecodeError:
            raise RuntimeError(f"{error_prefix}：上游返回非 JSON 响应")
        if not isinstance(data, dict):
            raise RuntimeError(f"{error_prefix}：上游返回格式异常")
        return data

    @staticmethod
    def _extract_responses_text(data: Dict[str, Any]) -> str:
        output_text = data.get("output_text")
        if isinstance(output_text, str) and output_text.strip():
            return output_text.strip()

        parts: List[str] = []
        output = data.get("output") or []
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict):
                    continue
                content = item.get("content") or []
                if isinstance(content, str):
                    parts.append(content)
                    continue
                if not isinstance(content, list):
                    continue
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    text = block.get("text") or block.get("content") or ""
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
        return "\n".join(parts).strip()
