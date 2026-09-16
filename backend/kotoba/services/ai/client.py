"""OpenAI-compatible chat client (DeepSeek by default)."""

from __future__ import annotations

import json
import re

import httpx
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.services import settings_store
from kotoba.services.ai.keys import ENV_KEY, get_api_key
from kotoba.services.ai.pricing import PRESETS, Usage

_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


class LLMClient:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key: str,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._client = httpx.Client(
            transport=transport,
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )

    def chat_json(self, system: str, user: str, max_tokens: int = 800) -> tuple[dict, Usage]:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.3,
            "max_tokens": max_tokens,
            "response_format": {"type": "json_object"},
        }
        try:
            resp = self._client.post(f"{self.base_url}/chat/completions", json=payload)
        except httpx.HTTPError as exc:
            raise ApiError("ai_failed", f"无法连接模型服务: {exc}", 502) from exc
        if resp.status_code >= 400:
            raise ApiError("ai_failed", f"模型服务返回 {resp.status_code}: {resp.text[:200]}", 502)
        data = resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ApiError("ai_failed", "模型响应格式异常", 502) from exc
        usage_raw = data.get("usage") or {}
        usage = Usage(
            prompt_tokens=int(usage_raw.get("prompt_tokens", 0)),
            completion_tokens=int(usage_raw.get("completion_tokens", 0)),
            cache_hit_tokens=int(usage_raw.get("prompt_cache_hit_tokens", 0)),
        )
        cleaned = _FENCE.sub("", content.strip())
        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as exc:
            raise ApiError("ai_failed", "模型未返回合法 JSON", 502) from exc
        if not isinstance(parsed, dict):
            raise ApiError("ai_failed", "模型返回的不是 JSON 对象", 502)
        return parsed, usage

    def close(self) -> None:
        self._client.close()


def client_from_settings(
    db: Session, transport: httpx.BaseTransport | None = None
) -> tuple[LLMClient, str]:
    provider = settings_store.get(db, "ai_provider") or "deepseek"
    base_url = (
        settings_store.get(db, "ai_base_url")
        or PRESETS.get(provider, PRESETS["custom"])["base_url"]
    )
    model = settings_store.get(db, "ai_model") or PRESETS.get(provider, PRESETS["custom"])["model"]
    key, _source = get_api_key(provider)
    if not key:
        raise ApiError(
            "ai_not_configured",
            f"尚未配置 {provider} 的 API Key：在设置页填写，或设置环境变量 {ENV_KEY}。",
            400,
        )
    return LLMClient(base_url, model, key, transport=transport), model
