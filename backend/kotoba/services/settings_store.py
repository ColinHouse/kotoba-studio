"""Key/value settings persisted in the settings table."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import Line, Setting

DEFAULTS: dict[str, Any] = {
    "review_owner_default": None,  # None → auto (mobile if a phone is registered, else desktop)
    "desired_retention": 0.9,
    "fsrs_parameters": None,  # personal parameters from the optimizer, None → library defaults
    "fsrs_parameters_previous": None,  # one-click restore of the pre-optimization values
    "ai_provider": "deepseek",
    "ai_base_url": "https://api.deepseek.com",
    "ai_model": "deepseek-flash",
    "ocr_provider": "auto",
    "preferred_text_source": "hook",  # recommendation only; both routes stay usable
    "active_session_id": None,
    "ui_language": "zh-CN",
    "capture_hotkey": "Ctrl+Shift+S",
    "capture_hotkey_enabled": False,
    "backfill_tolerance_s": 5.0,
    "video_dirs": [],  # directories the subtitle importer may read a video from
    "overlay_enabled": False,
    "overlay_hotkey": "Ctrl+Shift+O",
    "overlay_position": None,  # {"x": int, "y": int} for sessions without a work
}


def get(db: Session, key: str, default: Any = None) -> Any:
    row = db.get(Setting, key)
    if row is None:
        return DEFAULTS.get(key, default)
    return json.loads(row.value_json)


def set_value(db: Session, key: str, value: Any) -> None:
    row = db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value_json=json.dumps(value)))
    else:
        row.value_json = json.dumps(value)
    db.flush()


def all_values(db: Session) -> dict[str, Any]:
    out = dict(DEFAULTS)
    for row in db.scalars(select(Setting)).all():
        out[row.key] = json.loads(row.value_json)
    return out


def preferred_text_source(db: Session) -> str:
    """The explicit choice, or OCR first for a user who already mines with OCR.

    The key is new: before it existed, a user's route was whatever they had been
    using. Someone with OCR history keeps OCR first and sees no nudge to switch;
    only a user with no history gets the new default.
    """
    row = db.get(Setting, "preferred_text_source")
    if row is not None:
        return json.loads(row.value_json)
    has_ocr = db.scalar(select(Line.id).where(Line.origin == "ocr").limit(1))
    return "ocr" if has_ocr is not None else DEFAULTS["preferred_text_source"]


def public_values(db: Session) -> dict[str, Any]:
    """`all_values` with the text-source preference resolved for this user."""
    out = all_values(db)
    out["preferred_text_source"] = preferred_text_source(db)
    return out
