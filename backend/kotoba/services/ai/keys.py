"""API keys live in the OS credential store, never in the database."""

from __future__ import annotations

import os

from kotoba.core.errors import ApiError

KEYRING_SERVICE = "kotoba-studio"
ENV_KEY = "KOTOBA_AI_KEY"


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
