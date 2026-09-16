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
from kotoba.services.jp.normalize import normalize_ocr
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


class OcrCompareIn(BaseModel):
    region: RegionIn | None = None
    path: str | None = None


def _grabber(request: Request):
    return getattr(request.app.state, "capture_grabber", None) or screen.grab


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
        png = _grabber(request)(body.region.to_region()).png
    else:
        raise ApiError("validation_error", "region or path is required", 422)
    result = provider.recognize(png)
    return {**result.to_dict(), "normalized": normalize_ocr(result.text)}


@router.post("/ocr/compare")
def ocr_compare(body: OcrCompareIn, request: Request) -> list[dict]:
    if body.path:
        file = request.app.state.paths.media_dir / body.path
        if not file.is_file():
            raise ApiError("not_found", f"media {body.path} not found", 404)
        png = file.read_bytes()
    elif body.region:
        png = _grabber(request)(body.region.to_region()).png
    else:
        raise ApiError("validation_error", "region or path is required", 422)
    return registry.compare(png)


@router.post("/collect")
def collect(body: CollectIn, request: Request, db: Session = Depends(get_db)) -> dict:
    provider = _provider(request, db, body.provider)
    session_id = body.session_id
    if session_id is None:
        session_id = settings_store.get(db, "active_session_id")
    return collect_service.collect(
        db,
        request.app.state.paths,
        session_id,
        body.region.to_region(),
        provider,
        grabber=_grabber(request),
        source_id=body.source_id,
    )
