"""Clipboard watcher endpoints: start, stop, status."""

from __future__ import annotations

from fastapi import APIRouter, Request

from kotoba.services.capture.clipboard import ClipboardWatcher

router = APIRouter(prefix="/capture/clipboard", tags=["capture"])


def _watcher(request: Request) -> ClipboardWatcher:
    return request.app.state.clipboard_watcher


def _status(watcher: ClipboardWatcher) -> dict:
    return {"running": watcher.running, "captured": watcher.captured}


@router.post("/start")
def start(request: Request) -> dict:
    watcher = _watcher(request)
    watcher.start()
    return _status(watcher)


@router.post("/stop")
def stop(request: Request) -> dict:
    watcher = _watcher(request)
    watcher.stop()
    return _status(watcher)


@router.get("/status")
def status(request: Request) -> dict:
    return _status(_watcher(request))
