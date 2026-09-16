"""Game overlay endpoints: status, start, stop, toggle."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.services import settings_store
from kotoba.services.capture.hotkeys import HotkeyListener
from kotoba.services.overlay import DEFAULT_HOTKEY, OverlayController

router = APIRouter(prefix="/overlay", tags=["overlay"])


def _controller(request: Request) -> OverlayController:
    return request.app.state.overlay


def _listener(request: Request) -> HotkeyListener:
    return request.app.state.overlay_hotkey


def _status(request: Request) -> dict:
    listener = _listener(request)
    return {
        **_controller(request).status(),
        "hotkey": listener.hotkey,
        "hotkey_running": listener.running,
    }


@router.get("/status")
def status(request: Request) -> dict:
    return _status(request)


@router.post("/start")
def start(request: Request, db: Session = Depends(get_db)) -> dict:
    controller = _controller(request)
    listener = _listener(request)
    hotkey = settings_store.get(db, "overlay_hotkey") or DEFAULT_HOTKEY
    if listener.running and listener.hotkey != hotkey:
        listener.stop()
    listener.start(hotkey)
    controller.start()
    return _status(request)


@router.post("/stop")
def stop(request: Request) -> dict:
    _controller(request).stop()
    _listener(request).stop()
    return _status(request)


@router.post("/toggle")
def toggle(request: Request) -> dict:
    _controller(request).toggle()
    return _status(request)
