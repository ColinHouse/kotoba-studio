"""Global hotkey endpoints: status, start, stop."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.services import settings_store
from kotoba.services.capture.hotkeys import DEFAULT_HOTKEY, HotkeyListener, available

router = APIRouter(prefix="/capture/hotkeys", tags=["capture"])


def _listener(request: Request) -> HotkeyListener:
    return request.app.state.hotkey_listener


def _status(request: Request) -> dict:
    ok, note = available()
    return {"available": ok, "note": note, **_listener(request).status()}


@router.get("/status")
def status(request: Request) -> dict:
    return _status(request)


@router.post("/start")
def start(request: Request, db: Session = Depends(get_db)) -> dict:
    hotkey = settings_store.get(db, "capture_hotkey") or DEFAULT_HOTKEY
    listener = _listener(request)
    if listener.running and listener.hotkey != hotkey:
        listener.stop()
    listener.start(hotkey)
    return _status(request)


@router.post("/stop")
def stop(request: Request) -> dict:
    _listener(request).stop()
    return _status(request)
