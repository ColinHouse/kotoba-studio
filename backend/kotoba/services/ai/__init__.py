"""Optional AI explanations. Capture and review never depend on this."""

from kotoba.services.ai.client import LLMClient, client_from_settings
from kotoba.services.ai.keys import ENV_KEY, delete_api_key, get_api_key, set_api_key
from kotoba.services.ai.pricing import DEFAULT_PRICE, PRESETS, PRICES, Usage, estimate_cost

__all__ = [
    "DEFAULT_PRICE",
    "ENV_KEY",
    "LLMClient",
    "PRESETS",
    "PRICES",
    "Usage",
    "client_from_settings",
    "delete_api_key",
    "estimate_cost",
    "get_api_key",
    "set_api_key",
]
