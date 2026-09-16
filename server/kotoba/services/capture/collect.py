"""Screenshot → OCR → line, in one step (随手取词 / 收藏这句)."""

from __future__ import annotations

from collections.abc import Callable

from sqlalchemy.orm import Session

from kotoba.config import Paths
from kotoba.schemas import LineCreate, LineDTO
from kotoba.services.capture.screen import Grab, Region, grab, save_screenshot
from kotoba.services.jp.normalize import normalize_ocr
from kotoba.services.lines_service import create_line
from kotoba.services.ocr.base import OcrProvider

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
) -> dict:
    shot = grabber(region)
    result = provider.recognize(shot.png)
    text = normalize_ocr(result.text)
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
