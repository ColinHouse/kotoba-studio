"""Model presets and cost estimation.

Prices are USD per 1M tokens at peak rates, as published on
https://api-docs.deepseek.com/quick_start/pricing (checked 2026-09-16).
Off-peak is half. Tuple order: (input cache hit, input cache miss, output).
"""

from __future__ import annotations

from dataclasses import dataclass

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
