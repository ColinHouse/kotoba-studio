"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kotoba import __version__
from kotoba.api import (
    cards,
    devices,
    encounters,
    lines,
    meta,
    reviews,
    sessions,
    sources,
    terms,
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
    app.mount("/media", StaticFiles(directory=p.media_dir), name="media")
    return app


def app() -> FastAPI:
    """Factory entry point for `uvicorn kotoba.main:app --factory`."""
    return create_app()
