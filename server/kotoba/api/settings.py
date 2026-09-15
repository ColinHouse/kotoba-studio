"""User settings."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.services import settings_store

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
    for key, value in body.items():
        settings_store.set_value(db, key, value)
    db.commit()
    return settings_store.all_values(db)
