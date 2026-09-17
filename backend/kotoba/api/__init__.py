"""HTTP surface, grouped by domain.

Everything under ``/api`` is assembled here; the WebSocket routes are mounted
separately because they live at the root (``/ws/...``).
"""

from fastapi import APIRouter

from kotoba.api import meta
from kotoba.api.capture import (
    clipboard,
    condensed,
    epub,
    hooks,
    hotkeys,
    lines,
    mokuro,
    reader,
    screen,
    sessions,
    sources,
    subtitles,
    ws,
)
from kotoba.api.study import cards, encounters, kanji, quiz, reviews, stats, terms
from kotoba.api.system import ai, backups, devices, dictionary, export, overlay, settings

API_MODULES = (
    meta,
    sources,
    sessions,
    lines,
    screen,
    clipboard,
    hooks,
    hotkeys,
    subtitles,
    epub,
    mokuro,
    condensed,
    reader,
    dictionary,
    terms,
    encounters,
    cards,
    kanji,
    devices,
    reviews,
    quiz,
    stats,
    ai,
    export,
    backups,
    settings,
    overlay,
)


def build_api_router() -> APIRouter:
    """One router carrying every ``/api`` endpoint."""
    router = APIRouter(prefix="/api")
    for module in API_MODULES:
        router.include_router(module.router)
    return router


def build_websocket_router() -> APIRouter:
    """Root-level WebSocket routes (``/ws/events``, ``/ws/hook``)."""
    return ws.router
