# -*- coding: utf-8 -*-
"""通用 AI 文本客户端。

支持 OpenAI-compatible Chat Completions 与 OpenAI Responses 两类接口。
"""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Iterable, List, Optional

import requests


_OPENAI_HOST_RE = re.compile(r"(^|\.)api\.openai\.com$", re.IGNORECASE)
_OPENAI_REASONING_MODEL_RE = re.compile(r"^(?:o\d|gpt-5)(?:[-._].*)?$", re.IGNORECASE)


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

    def stream_text(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        top_p: float = 0.8,
        max_tokens: int = 800,
        timeout: int = 25,
    ) -> Iterable[str]:
        if self.api_type == "responses":
            yield from self._responses_stream(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
            )
            return
        yield from self._chat_completions_stream(
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

    def _is_openai_upstream(self) -> bool:
        if self.provider == "openai":
            return True
        try:
            from urllib.parse import urlparse

            host = (urlparse(self.base_url).hostname or "").strip()
            return bool(_OPENAI_HOST_RE.search(host))
        except Exception:
            return False

    @staticmethod
    def _is_openai_reasoning_model(model: str) -> bool:
        return bool(_OPENAI_REASONING_MODEL_RE.match((model or "").strip()))

    def _supports_sampling_params(self, model: str) -> bool:
        return not (self._is_openai_upstream() and self._is_openai_reasoning_model(model))

    def _chat_token_limit_param(self, model: str) -> str:
        if self._is_openai_upstream():
            return "max_completion_tokens"
        return "max_tokens"

    def _normalize_chat_messages(self, messages: List[Dict[str, str]], model: str) -> List[Dict[str, str]]:
        if not (self._is_openai_upstream() and self._is_openai_reasoning_model(model)):
            return [dict(msg) for msg in messages]

        normalized: List[Dict[str, str]] = []
        for msg in messages:
            role = str(msg.get("role") or "user").strip().lower() or "user"
            if role == "system":
                role = "developer"
            normalized.append({"role": role, "content": str(msg.get("content") or "")})
        return normalized

    @staticmethod
    def _with_sampling_params(
        payload: Dict[str, Any],
        *,
        temperature: float,
        top_p: float,
        include_sampling: bool,
    ) -> Dict[str, Any]:
        if not include_sampling:
            return dict(payload)
        return {
            **payload,
            "temperature": float(temperature),
            "top_p": float(top_p),
        }

    @staticmethod
    def _without_unsupported_optional_params(payload: Dict[str, Any]) -> Dict[str, Any]:
        return {
            key: value
            for key, value in payload.items()
            if key not in {"temperature", "top_p"}
        }

    @staticmethod
    def _looks_like_optional_param_error(error: Exception) -> bool:
        text = str(error).lower()
        if not text:
            return False
        return (
            ("temperature" in text or "top_p" in text)
            and ("unsupported" in text or "not support" in text or "not compatible" in text)
        )

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

        payload_base: Dict[str, Any] = {
            "model": model,
            "messages": self._normalize_chat_messages(messages, model),
            self._chat_token_limit_param(model): int(max_tokens),
        }
        payload = self._with_sampling_params(
            payload_base,
            temperature=temperature,
            top_p=top_p,
            include_sampling=self._supports_sampling_params(model),
        )
        data = self._post_json(
            f"{self.base_url}/chat/completions",
            payload,
            timeout,
            "AI Chat Completions 调用失败",
        )

        try:
            content = self._extract_chat_text(data)
        except Exception:
            content = ""
        if not content:
            raise RuntimeError("AI 未返回有效内容")
        return content

    def _chat_completions_stream(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        timeout: int,
    ) -> Iterable[str]:
        if not self.api_key:
            raise ValueError("AI_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("AI_BASE_URL 未配置")

        payload_base: Dict[str, Any] = {
            "model": model,
            "messages": self._normalize_chat_messages(messages, model),
            self._chat_token_limit_param(model): int(max_tokens),
            "stream": True,
        }
        payload = self._with_sampling_params(
            payload_base,
            temperature=temperature,
            top_p=top_p,
            include_sampling=self._supports_sampling_params(model),
        )
        yield from self._stream_sse(
            f"{self.base_url}/chat/completions",
            payload,
            timeout,
            self._extract_chat_stream_delta,
            "AI Chat Completions 流式调用失败",
        )

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

        payload_base: Dict[str, Any] = {
            "model": model,
            "input": [
                {
                    "role": str(msg.get("role") or "user"),
                    "content": str(msg.get("content") or ""),
                }
                for msg in messages
            ],
            "max_output_tokens": int(max_tokens),
        }
        payload = self._with_sampling_params(
            payload_base,
            temperature=temperature,
            top_p=top_p,
            include_sampling=self._supports_sampling_params(model),
        )
        data = self._post_json(
            f"{self.base_url}/responses",
            payload,
            timeout,
            "AI Responses 调用失败",
        )
        content = self._extract_responses_text(data)
        if content:
            return content
        if self._is_openai_upstream():
            return self._chat_completions(
                model=model,
                messages=messages,
                temperature=temperature,
                top_p=top_p,
                max_tokens=max_tokens,
                timeout=timeout,
            )
        raise RuntimeError("AI Responses 未返回有效内容")

    def _responses_stream(
        self,
        *,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float,
        top_p: float,
        max_tokens: int,
        timeout: int,
    ) -> Iterable[str]:
        if not self.api_key:
            raise ValueError("AI_API_KEY 未配置")
        if not self.base_url:
            raise ValueError("AI_BASE_URL 未配置")

        payload_base: Dict[str, Any] = {
            "model": model,
            "input": [
                {
                    "role": str(msg.get("role") or "user"),
                    "content": str(msg.get("content") or ""),
                }
                for msg in messages
            ],
            "max_output_tokens": int(max_tokens),
            "stream": True,
        }
        payload = self._with_sampling_params(
            payload_base,
            temperature=temperature,
            top_p=top_p,
            include_sampling=self._supports_sampling_params(model),
        )
        yield from self._stream_sse(
            f"{self.base_url}/responses",
            payload,
            timeout,
            self._extract_responses_stream_delta,
            "AI Responses 流式调用失败",
        )

    def _post_json(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: int,
        error_prefix: str,
    ) -> Dict[str, Any]:
        try:
            resp = requests.post(url, headers=self._headers(), json=payload, timeout=timeout)
            return self._json_or_raise(resp, error_prefix)
        except RuntimeError as exc:
            fallback_payload = self._without_unsupported_optional_params(payload)
            if fallback_payload == payload or not self._looks_like_optional_param_error(exc):
                raise
            resp = requests.post(url, headers=self._headers(), json=fallback_payload, timeout=timeout)
            return self._json_or_raise(resp, error_prefix)

    def _stream_sse(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: int,
        extract_delta,
        error_prefix: str,
    ) -> Iterable[str]:
        active_payload = payload
        retried = False
        while True:
            try:
                yield from self._stream_sse_once(url, active_payload, timeout, extract_delta, error_prefix)
                return
            except RuntimeError as exc:
                fallback_payload = self._without_unsupported_optional_params(active_payload)
                if retried or fallback_payload == active_payload or not self._looks_like_optional_param_error(exc):
                    raise
                active_payload = fallback_payload
                retried = True

    def _stream_sse_once(
        self,
        url: str,
        payload: Dict[str, Any],
        timeout: int,
        extract_delta,
        error_prefix: str,
    ) -> Iterable[str]:
        with requests.post(
            url,
            headers=self._headers(),
            json=payload,
            timeout=timeout,
            stream=True,
        ) as resp:
            if resp.status_code < 200 or resp.status_code >= 300:
                msg = ""
                try:
                    js = self._response_json(resp)
                    msg = js.get("error", {}).get("message") or js.get("message") or ""
                except Exception:
                    text = self._response_text(resp)
                    msg = text[:300] if text else ""
                raise RuntimeError(f"{error_prefix}：HTTP {resp.status_code} {msg}".strip())

            emitted = False
            emitted_text = ""
            for raw_line in resp.iter_lines(decode_unicode=False):
                if raw_line is None:
                    continue
                if isinstance(raw_line, bytes):
                    line = raw_line.decode("utf-8", errors="replace").strip()
                else:
                    line = str(raw_line).strip()
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                data_text = line[5:].strip()
                if not data_text or data_text == "[DONE]":
                    break
                try:
                    data = json.loads(data_text)
                except json.JSONDecodeError:
                    continue
                delta = extract_delta(data)
                delta = self._normalize_stream_delta(delta, emitted_text)
                if delta:
                    emitted = True
                    emitted_text += delta
                    yield delta
            if not emitted:
                raise RuntimeError(f"{error_prefix}：上游未返回有效流式内容")

    @staticmethod
    def _normalize_stream_delta(delta: Any, emitted_text: str) -> str:
        """兼容少数上游把累计全文快照放在流式 delta 中返回的情况。"""
        text = str(delta or "")
        if not text or not emitted_text:
            return text
        if text == emitted_text:
            return ""
        if len(text) > len(emitted_text) and text.startswith(emitted_text):
            return text[len(emitted_text):]
        return text

    @staticmethod
    def _extract_chat_stream_delta(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        delta = (choices[0] or {}).get("delta") or {}
        text = delta.get("content") or ""
        if isinstance(text, list):
            return "".join(
                str(item.get("text") or item.get("content") or "")
                if isinstance(item, dict) else str(item)
                for item in text
            )
        return str(text or "")

    @staticmethod
    def _extract_responses_stream_delta(data: Dict[str, Any]) -> str:
        event_type = str(data.get("type") or "")
        if event_type in {"response.output_text.delta", "response.refusal.delta"}:
            return str(data.get("delta") or "")
        if event_type:
            return ""

        delta = data.get("delta")
        if isinstance(delta, str):
            return delta

        item = data.get("item") or {}
        if isinstance(item, dict):
            content = item.get("content") or []
            if isinstance(content, list):
                parts = []
                for block in content:
                    if isinstance(block, dict):
                        parts.append(str(block.get("text") or block.get("content") or ""))
                return "".join(parts)

        return ""

    @staticmethod
    def _json_or_raise(resp: requests.Response, error_prefix: str) -> Dict[str, Any]:
        data = None
        try:
            data = AIClient._response_json(resp)
        except RuntimeError:
            data = None

        if resp.status_code < 200 or resp.status_code >= 300:
            msg = ""
            if isinstance(data, dict):
                msg = data.get("error", {}).get("message") or data.get("message") or ""
            if not msg:
                text = AIClient._response_text(resp)
                msg = text[:300] if text else ""
            raise RuntimeError(f"{error_prefix}：HTTP {resp.status_code} {msg}".strip())

        if not isinstance(data, dict):
            raise RuntimeError(f"{error_prefix}：上游返回非 JSON 响应")
        return data

    @staticmethod
    def _response_text(resp: requests.Response) -> str:
        raw = getattr(resp, "content", None)
        if isinstance(raw, bytes) and raw:
            return raw.decode("utf-8", errors="replace")
        text = getattr(resp, "text", "")
        return text if isinstance(text, str) else str(text or "")

    @staticmethod
    def _response_json(resp: requests.Response) -> Dict[str, Any]:
        text = AIClient._response_text(resp)
        if text:
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    return data
            except json.JSONDecodeError:
                pass
        try:
            data = resp.json()
        except json.JSONDecodeError as exc:
            raise RuntimeError("上游返回非 JSON 响应") from exc
        except Exception as exc:
            raise RuntimeError("上游返回非 JSON 响应") from exc
        if not isinstance(data, dict):
            raise RuntimeError("上游返回格式异常")
        return data

    @staticmethod
    def _extract_chat_text(data: Dict[str, Any]) -> str:
        choices = data.get("choices") or []
        if not choices:
            return ""
        msg = (choices[0] or {}).get("message") or {}
        content = msg.get("content") or ""
        if isinstance(content, list):
            parts = []
            for block in content:
                if isinstance(block, dict):
                    parts.append(str(block.get("text") or block.get("content") or ""))
                else:
                    parts.append(str(block or ""))
            return "".join(parts).strip()
        return str(content or "").strip()

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
        text = "\n".join(parts).strip()
        if text:
            return text
        return AIClient._extract_chat_text(data)
