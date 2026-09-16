"""User settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fsrs import Scheduler
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.services import settings_store
from kotoba.services.ai import keys
from kotoba.services.capture import hotkeys

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
def get_settings(db: Session = Depends(get_db)) -> dict[str, Any]:
    return settings_store.all_values(db)


@router.put("")
def put_settings(body: dict[str, Any], db: Session = Depends(get_db)) -> dict[str, Any]:
    unknown = [k for k in body if k not in settings_store.DEFAULTS]
    if unknown:
        raise ApiError("unknown_setting", f"unknown setting(s): {', '.join(unknown)}")
    if "desired_retention" in body:
        value = float(body["desired_retention"])
        if not 0.7 <= value <= 0.99:
            raise ApiError("invalid_value", "desired_retention must be between 0.7 and 0.99")
        body["desired_retention"] = value
    if "review_owner_default" in body and body["review_owner_default"] not in (
        None,
        "desktop",
        "mobile",
        "any",
    ):
        raise ApiError("invalid_value", "review_owner_default must be desktop/mobile/any/null")
    if body.get("fsrs_parameters") is not None:
        try:
            Scheduler(parameters=[float(value) for value in body["fsrs_parameters"]])
        except (TypeError, ValueError) as exc:
            raise ApiError("invalid_value", f"fsrs_parameters 无效：{exc}") from exc
    if "capture_hotkey" in body:
        hotkey = str(body["capture_hotkey"]).strip()
        try:
            hotkeys.normalize_hotkey(hotkey)
        except ValueError as exc:
            raise ApiError("invalid_value", f"快捷键无效：{exc}") from exc
        body["capture_hotkey"] = hotkey
    for key, value in body.items():
        settings_store.set_value(db, key, value)
    db.commit()
    return settings_store.all_values(db)


class AiKeyIn(BaseModel):
    provider: str = Field(min_length=1, max_length=40)
    key: str = Field(min_length=1)


@router.get("/ai-key")
def ai_key_status(db: Session = Depends(get_db)) -> dict:
    provider = settings_store.get(db, "ai_provider") or "deepseek"
    key, source = keys.get_api_key(provider)
    return {"provider": provider, "configured": bool(key), "source": source}


@router.put("/ai-key")
def put_ai_key(body: AiKeyIn, db: Session = Depends(get_db)) -> dict:
    keys.set_api_key(body.provider, body.key.strip())
    settings_store.set_value(db, "ai_provider", body.provider)
    db.commit()
    key, source = keys.get_api_key(body.provider)
    return {"provider": body.provider, "configured": bool(key), "source": source}


@router.delete("/ai-key")
def delete_ai_key(db: Session = Depends(get_db)) -> dict:
    provider = settings_store.get(db, "ai_provider") or "deepseek"
    keys.delete_api_key(provider)
    return {"provider": provider, "configured": False, "source": "none"}
