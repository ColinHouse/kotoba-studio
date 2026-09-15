"""Key/value settings persisted in the settings table."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import Setting

DEFAULTS: dict[str, Any] = {
    "review_owner_default": None,  # None → auto (mobile if a phone is registered, else desktop)
    "desired_retention": 0.9,
    "ai_provider": "deepseek",
    "ai_base_url": "https://api.deepseek.com",
    "ai_model": "deepseek-chat",
    "ocr_provider": "auto",
    "active_session_id": None,
    "ui_language": "zh-CN",
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
