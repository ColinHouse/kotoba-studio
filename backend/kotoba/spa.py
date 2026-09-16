"""Serve the built frontend (``frontend/dist``) with history-mode fallback."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kotoba.core.config import Settings

RESERVED_PREFIXES = ("api/", "media/", "ws/", "assets/")


def default_dist() -> Path:
    """`frontend/dist` as laid out in the repository."""
    return Path(__file__).resolve().parents[2] / "frontend" / "dist"


def mount(app: FastAPI, settings: Settings) -> bool:
    """Mount the SPA if it has been built. Returns whether anything was mounted."""
    dist = settings.web_dist or default_dist()
    if not (dist / "index.html").is_file():
        return False
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str) -> FileResponse:
        if path.startswith(RESERVED_PREFIXES) or path in ("api", "media"):
            raise HTTPException(status_code=404, detail="not found")
        candidate = (dist / path).resolve() if path else dist / "index.html"
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")

    return True
