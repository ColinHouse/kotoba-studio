"""Device registration (desktop / mobile) for review ownership."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Device, utcnow

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceRegister(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: Literal["desktop", "mobile"]
    id: str | None = None


def device_to_dict(d: Device) -> dict:
    return {
        "id": d.id,
        "name": d.name,
        "kind": d.kind,
        "created_at": d.created_at.isoformat(),
        "last_seen": d.last_seen.isoformat(),
    }


def get_device_or_404(db: Session, device_id: str) -> Device:
    d = db.get(Device, device_id)
    if d is None:
        raise ApiError("unknown_device", f"device {device_id} is not registered", 404)
    return d


@router.post("/register")
def register(body: DeviceRegister, db: Session = Depends(get_db)) -> dict:
    device = db.get(Device, body.id) if body.id else None
    if device is None:
        device = Device(id=body.id or uuid.uuid4().hex, name=body.name, kind=body.kind)
        db.add(device)
    else:
        device.name, device.kind, device.last_seen = body.name, body.kind, utcnow()
    db.commit()
    return device_to_dict(device)


@router.get("")
def list_devices(db: Session = Depends(get_db)) -> list[dict]:
    return [device_to_dict(d) for d in db.scalars(select(Device).order_by(Device.created_at)).all()]


@router.delete("/{device_id}", status_code=204)
def delete_device(device_id: str, db: Session = Depends(get_db)) -> None:
    db.delete(get_device_or_404(db, device_id))
    db.commit()
