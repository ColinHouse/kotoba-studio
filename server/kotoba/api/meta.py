"""Health and instance metadata."""

from __future__ import annotations

import platform

from fastapi import APIRouter

from kotoba import __version__

router = APIRouter(tags=["meta"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok", "version": __version__, "platform": platform.system().lower()}
