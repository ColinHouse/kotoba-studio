"""Parse a hook message: plain text or JSON {"text": ..., "speaker"?: ...}."""

from __future__ import annotations

import json


def parse_hook_message(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict) and data.get("text"):
                return data
        except json.JSONDecodeError:
            pass
    return {"text": raw}
