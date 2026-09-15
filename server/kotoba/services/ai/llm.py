"""OpenAI-compatible chat client (DeepSeek by default) with key storage and cost estimates."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass

import httpx
from sqlalchemy.orm import Session

from kotoba.errors import ApiError
from kotoba.services import settings_store

KEYRING_SERVICE = "kotoba-studio"
ENV_KEY = "KOTOBA_AI_KEY"

# USD per 1M tokens at peak rates: (input cache hit, input cache miss, output). Verified 2026-09-16
# at https://api-docs.deepseek.com/quick_start/pricing (off-peak is half).
PRICES: dict[str, tuple[float, float, float]] = {
    "deepseek-flash": (0.006, 0.30, 1.20),
    "deepseek-v4-pro": (0.044, 1.32, 3.96),
}
DEFAULT_PRICE = (0.05, 0.50, 1.50)

PRESETS: dict[str, dict[str, str]] = {
    "deepseek": {"base_url": "https://api.deepseek.com", "model": "deepseek-flash"},
    "openai": {"base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini"},
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "model": "qwen-flash",
    },
    "moonshot": {"base_url": "https://api.moonshot.cn/v1", "model": "kimi-k2-turbo-preview"},
    "custom": {"base_url": "http://localhost:11434/v1", "model": "qwen3"},
}


@dataclass(slots=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_hit_tokens: int = 0


def estimate_cost(model: str, usage: Usage) -> float:
    hit, miss, out = PRICES.get(model, DEFAULT_PRICE)
    miss_tokens = max(usage.prompt_tokens - usage.cache_hit_tokens, 0)
    return (usage.cache_hit_tokens * hit + miss_tokens * miss + usage.completion_tokens * out) / 1e6


def get_api_key(provider: str) -> tuple[str | None, str]:
    """Return (key, source) where source is env / keyring / none."""
    env = os.environ.get(ENV_KEY)
    if env:
        return env, "env"
    try:
        import keyring

        key = keyring.get_password(KEYRING_SERVICE, provider)
    except Exception:  # noqa: BLE001 - no backend, locked keychain, etc.
        key = None
    return (key, "keyring") if key else (None, "none")


def set_api_key(provider: str, key: str) -> None:
    try:
        import keyring

        keyring.set_password(KEYRING_SERVICE, provider, key)
    except Exception as exc:  # noqa: BLE001
        raise ApiError(
            "keyring_unavailable",
            f"无法写入系统凭据存储（{exc}）。可改为设置环境变量 {ENV_KEY}。",
            500,
        ) from exc


def delete_api_key(provider: str) -> None:
    try:
        import keyring

        keyring.delete_password(KEYRING_SERVICE, provider)
    except Exception:  # noqa: BLE001
        pass


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
