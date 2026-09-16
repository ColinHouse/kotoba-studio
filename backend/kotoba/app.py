"""FastAPI application factory.

One process owns everything: the JSON API, the WebSocket ingest, the media
files and the built web app. That keeps a phone on the same network one URL
away from the same data the desktop sees.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from kotoba import __version__, spa
from kotoba.api import build_api_router, build_websocket_router
from kotoba.core.config import Settings, get_settings, paths
from kotoba.core.db import Database, make_engine, upgrade
from kotoba.core.errors import install_error_handlers
from kotoba.services import settings_store
from kotoba.services.capture.buffer import MediaBuffer
from kotoba.services.capture.clipboard import ClipboardWatcher
from kotoba.services.capture.hook_client import HookManager
from kotoba.services.capture.hotkeys import DEFAULT_HOTKEY, HotkeyListener, make_collector
from kotoba.services.ocr import registry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    resolved_paths = paths(settings).ensure()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        upgrade(resolved_paths.db_path)
        app.state.settings = settings
        app.state.paths = resolved_paths
        app.state.db = Database(make_engine(resolved_paths.db_path))
        # Resolve the database per use: restore_backup() swaps app.state.db, and a
        # captured bound method would keep writing through the retired engine.
        app.state.clipboard_watcher = ClipboardWatcher(lambda: app.state.db.session())
        app.state.clipboard_watcher = ClipboardWatcher(lambda: app.state.db.session())
        app.state.hook_manager = HookManager(lambda: app.state.db.session())
        app.state.region_watcher = None
        app.state.media_buffer = MediaBuffer()
        app.state.hotkey_listener = HotkeyListener(
            make_collector(
                lambda: app.state.db.session(),
                resolved_paths,
                lambda db: registry.get_provider(settings_store.get(db, "ocr_provider")),
                lambda: getattr(app.state, "region_watcher", None),
            )
        )
        db = app.state.db.session()
        try:
            if settings_store.get(db, "capture_hotkey_enabled"):
                app.state.hotkey_listener.start(
                    settings_store.get(db, "capture_hotkey") or DEFAULT_HOTKEY
                )
        finally:
            db.close()
        try:
            yield
        finally:
            app.state.hotkey_listener.stop()
            watcher = app.state.region_watcher
            if watcher is not None:
                watcher.stop()
            await app.state.hook_manager.shutdown()
            app.state.clipboard_watcher.stop()
            app.state.db.dispose()

    app = FastAPI(title="Kotoba Studio", version=__version__, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    install_error_handlers(app)

    app.include_router(build_api_router())
    app.include_router(build_websocket_router())
    app.mount("/media", StaticFiles(directory=resolved_paths.media_dir), name="media")
    spa.mount(app, settings)
    return app


def app() -> FastAPI:
    """Factory entry point for `uvicorn kotoba.app:app --factory`."""
    return create_app()
