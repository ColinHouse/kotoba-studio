"""Desktop-only capture endpoints: displays, screenshots, OCR, collect."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.services import settings_store
from kotoba.services.capture import collect as collect_service
from kotoba.services.capture import screen
from kotoba.services.capture import windows as windows_service
from kotoba.services.capture.watcher import RegionWatcher
from kotoba.services.dictionary.lookup import has_form
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.jp.repair import repair_ocr
from kotoba.services.ocr import registry

router = APIRouter(prefix="/capture", tags=["capture"])


class RegionIn(BaseModel):
    left: int = 0
    top: int = 0
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    display: int = 0

    def to_region(self) -> screen.Region:
        return screen.Region(self.left, self.top, self.width, self.height, self.display)


class ScreenshotIn(BaseModel):
    display: int = 0
    region: RegionIn | None = None


class OcrIn(BaseModel):
    region: RegionIn | None = None
    path: str | None = None
    provider: str | None = None


class CollectIn(BaseModel):
    region: RegionIn
    session_id: int | None = None
    source_id: int | None = None
    provider: str | None = None


class WatchIn(BaseModel):
    region: RegionIn
    source_id: int | None = None


class OcrCompareIn(BaseModel):
    region: RegionIn | None = None
    path: str | None = None


def _grabber(request: Request):
    return getattr(request.app.state, "capture_grabber", None) or screen.grab


def _overlay_rect(request: Request) -> tuple[int, int, int, int] | None:
    overlay = getattr(request.app.state, "overlay", None)
    return overlay.screen_rect() if overlay is not None else None


def _masked(request: Request, shot: screen.Grab) -> bytes:
    """OCR input from a screen grab, with our own overlay blacked out.

    Window grabs come from `PrintWindow` and never contain the panel, so only
    the screen path needs this.
    """
    rect = _overlay_rect(request)
    if rect is None or shot.source != "screen":
        return shot.png
    return screen.mask_rect(shot.png, rect, origin=shot.origin, scale=shot.scale)


def _provider(request: Request, db: Session, name: str | None):
    override = getattr(request.app.state, "ocr_provider", None)
    if override is not None and name in (None, "", "auto"):
        return override
    return registry.get_provider(name or settings_store.get(db, "ocr_provider"))


@router.get("/displays")
def list_displays(request: Request) -> list[dict]:
    fn = getattr(request.app.state, "capture_displays", None) or screen.displays
    return fn()


@router.get("/providers")
def list_providers() -> list[dict]:
    return registry.list_providers()


@router.get("/windows")
def list_game_windows() -> list[dict]:
    """Visible top-level windows a game could be running in, biggest first."""
    if not windows_service.available():
        return []
    return [w.to_dict() for w in windows_service.list_windows()]


@router.post("/screenshot")
def screenshot(body: ScreenshotIn, request: Request) -> dict:
    grabber = _grabber(request)
    if body.region is not None:
        shot = grabber(body.region.to_region())
        region = body.region.model_dump()
    else:
        fn = getattr(request.app.state, "capture_displays", None) or screen.displays
        mons = fn()
        if not 0 <= body.display < len(mons):
            raise ApiError("invalid_region", f"显示器 {body.display} 不存在")
        mon = mons[body.display]
        region = {
            "left": 0,
            "top": 0,
            "width": mon["width"],
            "height": mon["height"],
            "display": body.display,
        }
        shot = grabber(screen.Region(**region))
    path = screen.save_screenshot(shot.png, request.app.state.paths, subdir="previews")
    return {
        "path": path,
        "width": shot.width,
        "height": shot.height,
        "scale": shot.scale,
        "region": region,
    }


@router.post("/ocr")
def ocr(body: OcrIn, request: Request, db: Session = Depends(get_db)) -> dict:
    provider = _provider(request, db, body.provider)
    if body.path:
        file = request.app.state.paths.media_dir / body.path
        if not file.is_file():
            raise ApiError("not_found", f"media {body.path} not found", 404)
        png = file.read_bytes()
    elif body.region:
        png = _masked(request, _grabber(request)(body.region.to_region()))
    else:
        raise ApiError("validation_error", "region or path is required", 422)
    result = provider.recognize(png)
    text = normalize_ocr(result.text)
    return {**result.to_dict(), "normalized": repair_ocr(text, lambda form: has_form(db, form))}


@router.post("/ocr/compare")
def ocr_compare(body: OcrCompareIn, request: Request) -> list[dict]:
    if body.path:
        file = request.app.state.paths.media_dir / body.path
        if not file.is_file():
            raise ApiError("not_found", f"media {body.path} not found", 404)
        png = file.read_bytes()
    elif body.region:
        png = _masked(request, _grabber(request)(body.region.to_region()))
    else:
        raise ApiError("validation_error", "region or path is required", 422)
    return registry.compare(png)


@router.post("/collect")
def collect(body: CollectIn, request: Request, db: Session = Depends(get_db)) -> dict:
    provider = _provider(request, db, body.provider)
    session_id = body.session_id
    if session_id is None:
        session_id = settings_store.get(db, "active_session_id")
    # No window lookup here: collect() asks capture_trust(), which resolves the
    # window once and decides whether capturing is safe at the same time.
    return collect_service.collect(
        db,
        request.app.state.paths,
        session_id,
        body.region.to_region(),
        provider,
        grabber=_grabber(request),
        source_id=body.source_id,
        mask=lambda: _overlay_rect(request),
    )


def _watcher_status(watcher: RegionWatcher | None) -> dict:
    if watcher is None:
        return {"running": False, "captured": 0, "last_error": None, "paused_reason": None}
    return {
        "running": watcher.running,
        "captured": watcher.captured,
        "last_error": watcher.last_error,
        # Running but refusing to write: the UI must say so, or the watcher looks
        # busy while it is quietly collecting nothing.
        "paused_reason": watcher.paused_reason,
    }


@router.post("/watch/start")
def watch_start(body: WatchIn, request: Request, db: Session = Depends(get_db)) -> dict:
    watcher = getattr(request.app.state, "region_watcher", None)
    if watcher is not None and watcher.running:
        return _watcher_status(watcher)

    def source_window() -> windows_service.WindowInfo | None:
        if body.source_id is None or not windows_service.available():
            return None
        session = request.app.state.db.session()
        try:
            return windows_service.window_for_source(session, body.source_id)
        finally:
            session.close()

    base_grabber = _grabber(request)

    def grabber(region: screen.Region) -> screen.Grab:
        window = source_window()
        shot = windows_service.grab_from_window(window, region) if window else None
        return shot if shot is not None else base_grabber(region)

    def region_provider() -> screen.Region | None:
        """Re-resolve every cycle: the game window may have moved or resized."""
        session = request.app.state.db.session()
        try:
            return windows_service.resolve_region(session, body.source_id)  # type: ignore[arg-type]
        finally:
            session.close()

    watcher = RegionWatcher(
        body.region.to_region(),
        lambda: request.app.state.db.session(),
        _provider(request, db, None),
        grabber=grabber,
        region_provider=region_provider if body.source_id is not None else None,
        source_id=body.source_id,
        buffer=getattr(request.app.state, "media_buffer", None),
        mask=lambda: _overlay_rect(request),
    )
    request.app.state.region_watcher = watcher
    watcher.start()
    return _watcher_status(watcher)


@router.post("/watch/stop")
def watch_stop(request: Request) -> dict:
    watcher = getattr(request.app.state, "region_watcher", None)
    if watcher is not None:
        watcher.stop()
    return _watcher_status(watcher)


@router.get("/watch/status")
def watch_status(request: Request) -> dict:
    return _watcher_status(getattr(request.app.state, "region_watcher", None))
