"""Screenshot → OCR → line, in one step (随手取词 / 收藏这句)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.core.errors import ApiError
from kotoba.schemas import LineCreate, LineDTO
from kotoba.services.capture.screen import Grab, Region, grab, save_screenshot
from kotoba.services.capture.windows import WindowInfo, capture_trust, grab_from_window
from kotoba.services.dictionary.lookup import has_form
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.jp.repair import repair_ocr
from kotoba.services.ocr.base import OcrProvider
from kotoba.services.text.ingest import create_line

Grabber = Callable[[Region], Grab]


def collect(
    db: Session,
    paths: Paths,
    session_id: int | None,
    region: Region,
    provider: OcrProvider,
    grabber: Grabber = grab,
    source_id: int | None = None,
    save: bool = True,
    window: WindowInfo | None = None,
) -> dict:
    """`window` overrides the one `capture_trust` resolves; only tests pass it."""
    # Refuse before grabbing anything: if the bound game is not the window the
    # user is looking at, every pixel in this region belongs to something else.
    trust = capture_trust(db, source_id)
    if not trust.ok:
        raise ApiError("capture_blocked", trust.message)
    # The window's own pixels are still preferred -- they survive our own overlay
    # sitting on top. PrintWindow returns nothing for plenty of real games, and
    # falling back to the screen is correct *because* trust just established that
    # the game is the foreground window.
    target = window if window is not None else trust.window
    shot = grab_from_window(target, region) if target is not None else None
    if shot is None:
        shot = grabber(region)
    result = provider.recognize(shot.png)
    text = normalize_ocr(result.text)
    text = repair_ocr(text, lambda form: has_form(db, form))
    # Only keep the screenshot when there is text to attach it to (no orphan files).
    screenshot_path = save_screenshot(shot.png, paths) if (save and text) else None
    payload = {
        "ocr": result.to_dict(),
        "screenshot_path": screenshot_path,
        "scale": shot.scale,
        "line": None,
        "duplicate": False,
    }
    if not text:
        return payload
    line, duplicate = create_line(
        db,
        LineCreate(
            session_id=session_id,
            source_id=source_id,
            text=text,
            raw_text=result.text,
            origin="ocr",
            screenshot_path=screenshot_path,
            position={"region": region.to_dict()},
        ),
    )
    payload["line"] = LineDTO.from_model(line, 0).model_dump(mode="json")
    payload["duplicate"] = duplicate
    return payload
