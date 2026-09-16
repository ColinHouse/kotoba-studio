"""Shared DTO helpers and literal types."""

from __future__ import annotations

import json
from typing import Any, Literal

Kind = Literal["game", "anime", "video", "manga", "other"]
LineStatus = Literal["inbox", "kept", "discarded"]
SessionMode = Literal["quick", "companion", "import"]
TextSource = Literal["ocr", "hook", "subtitle", "manual"]
LineOrigin = Literal["manual", "hook", "ocr", "subtitle"]


def loads(value: str | None) -> Any:
    """Parse a JSON column that may be NULL."""
    return json.loads(value) if value else None
