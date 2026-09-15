"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from kotoba import __version__
from kotoba.api import (
    ai,
    backups,
    capture,
    cards,
    devices,
    encounters,
    export,
    lines,
    meta,
    quiz,
    reviews,
    sessions,
    sources,
    terms,
    ws,
)
from kotoba.api import dict as dict_api
from kotoba.api import (
    settings as settings_api,
)
from kotoba.config import Settings, get_settings, paths
from kotoba.db import Database, make_engine, upgrade
from kotoba.errors import install_error_handlers


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    p = paths(settings).ensure()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        upgrade(p.db_path)
        app.state.settings = settings
        app.state.paths = p
        app.state.db = Database(make_engine(p.db_path))
        try:
            yield
        finally:
            app.state.db.dispose()

    app = FastAPI(title="Kotoba Studio", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    app.include_router(meta.router, prefix="/api")
    app.include_router(dict_api.router, prefix="/api")
    app.include_router(sources.router, prefix="/api")
    app.include_router(sessions.router, prefix="/api")
    app.include_router(lines.router, prefix="/api")
    app.include_router(terms.router, prefix="/api")
    app.include_router(encounters.router, prefix="/api")
    app.include_router(cards.router, prefix="/api")
    app.include_router(devices.router, prefix="/api")
    app.include_router(reviews.router, prefix="/api")
    app.include_router(settings_api.router, prefix="/api")
    app.include_router(capture.router, prefix="/api")
    app.include_router(quiz.router, prefix="/api")
    app.include_router(ai.router, prefix="/api")
    app.include_router(export.router, prefix="/api")
    app.include_router(backups.router, prefix="/api")
    app.include_router(ws.router)
    app.mount("/media", StaticFiles(directory=p.media_dir), name="media")
    _mount_spa(app, settings)
    return app


def default_web_dist() -> Path:
    return Path(__file__).resolve().parents[2] / "web" / "dist"


def _mount_spa(app: FastAPI, settings: Settings) -> None:
    """Serve the built Vue app (web/dist) with history-mode fallback."""
    dist = settings.web_dist or default_web_dist()
    if not (dist / "index.html").is_file():
        return
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith(("api/", "media/", "ws/", "assets/")) or path in ("api", "media"):
            raise HTTPException(status_code=404, detail="not found")
        candidate = (dist / path).resolve() if path else dist / "index.html"
        if path and candidate.is_file() and dist.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(dist / "index.html")


def app() -> FastAPI:
    """Factory entry point for `uvicorn kotoba.main:app --factory`."""
    return create_app()
