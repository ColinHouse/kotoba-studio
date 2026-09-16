"""HTTP surface, grouped by domain.

Everything under ``/api`` is assembled here; the WebSocket routes are mounted
separately because they live at the root (``/ws/...``).
"""

from fastapi import APIRouter

from kotoba.api import meta
from kotoba.api.capture import clipboard, hooks, lines, screen, sessions, sources, ws
from kotoba.api.study import cards, encounters, quiz, reviews, terms
from kotoba.api.system import ai, backups, devices, dictionary, export, settings

API_MODULES = (
    meta,
    sources,
    sessions,
    lines,
    screen,
    clipboard,
    hooks,
    dictionary,
    terms,
    encounters,
    cards,
    devices,
    reviews,
    quiz,
    ai,
    export,
    backups,
    settings,
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
