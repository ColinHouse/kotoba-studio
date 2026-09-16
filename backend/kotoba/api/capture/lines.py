"""Captured lines (台词) and their analysis."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import Encounter, Line
from kotoba.schemas import LineCreate, LineCreated, LineDTO, LineUpdate
from kotoba.services import settings_store
from kotoba.services.capture import screen
from kotoba.services.jp.normalize import normalize_ocr, text_hash
from kotoba.services.learning import ranking
from kotoba.services.text import analysis
from kotoba.services.text.ingest import create_line

router = APIRouter(prefix="/lines", tags=["lines"])


def get_line_or_404(db: Session, line_id: int) -> Line:
    line = db.get(Line, line_id)
    if line is None:
        raise ApiError("not_found", f"line {line_id} not found", 404)
    return line


def _encounter_count(db: Session, line_id: int) -> int:
    return db.scalar(select(func.count(Encounter.id)).where(Encounter.line_id == line_id)) or 0


@router.get("")
def list_lines(
    session_id: int | None = None,
    source_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    sort: Literal["recent", "iplus1"] = "recent",
    db: Session = Depends(get_db),
) -> list[LineDTO]:
    stmt = select(Line).order_by(
        Line.ord.is_(None), Line.ord.asc(), Line.captured_at.desc(), Line.id.desc()
    )
    if session_id is not None:
        stmt = stmt.where(Line.session_id == session_id)
    if source_id is not None:
        stmt = stmt.where(Line.source_id == source_id)
    if status is not None:
        stmt = stmt.where(Line.status == status)

    if sort == "iplus1":
        # Rank a recent window rather than the whole library: every uncached line
        # costs a tokenization, and the inbox only asks for a page anyway.
        candidates = list(db.scalars(stmt.limit(ranking.SCAN_LIMIT)).all())
        counts = {line.id: ranking.enrich(db, line) for line in candidates}
        db.commit()
        candidates.sort(key=lambda line: ranking.sort_key(counts[line.id]))
        lines = candidates[offset : offset + limit]
    else:
        lines = list(db.scalars(stmt.limit(limit).offset(offset)).all())

    return [LineDTO.from_model(line, _encounter_count(db, line.id)) for line in lines]


@router.post("", response_model=LineCreated)
def post_line(body: LineCreate, response: Response, db: Session = Depends(get_db)) -> LineCreated:
    line, duplicate = create_line(db, body)
    response.status_code = 200 if duplicate else 201
    return LineCreated(
        line=LineDTO.from_model(line, _encounter_count(db, line.id)), duplicate=duplicate
    )


@router.get("/{line_id}")
def get_line(line_id: int, db: Session = Depends(get_db)) -> LineDTO:
    line = get_line_or_404(db, line_id)
    return LineDTO.from_model(line, _encounter_count(db, line.id))


@router.patch("/{line_id}")
def update_line(line_id: int, body: LineUpdate, db: Session = Depends(get_db)) -> LineDTO:
    line = get_line_or_404(db, line_id)
    data = body.model_dump(exclude_unset=True)
    if "text" in data:
        line.text = normalize_ocr(data.pop("text"))
        line.text_hash = text_hash(line.text)
        line.tokens_json = None
        line.unknown_count = None
    for key, value in data.items():
        setattr(line, key, value)
    db.commit()
    return LineDTO.from_model(line, _encounter_count(db, line.id))


@router.delete("/{line_id}", status_code=204)
def delete_line(line_id: int, db: Session = Depends(get_db)) -> None:
    line = get_line_or_404(db, line_id)
    db.delete(line)
    db.commit()


@router.post("/{line_id}/analyze")
def analyze(line_id: int, force: bool = False, db: Session = Depends(get_db)) -> dict:
    line = get_line_or_404(db, line_id)
    return analysis.analyze_line(db, line, force=force)


def _save_audio(data: bytes, paths: Paths) -> str:
    """Write a buffered chunk under media/audio/YYYYMMDD/ and return the media-relative path."""
    day = datetime.now(UTC).strftime("%Y%m%d")
    folder = paths.audio_dir / day
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{uuid4().hex}.bin"
    (folder / name).write_bytes(data)
    return f"audio/{day}/{name}"


@router.post("/{line_id}/backfill")
def backfill_line(
    line_id: int, request: Request, force: bool = False, db: Session = Depends(get_db)
) -> dict:
    """Fill a line's screenshot/audio from the rolling buffer, after the fact.

    Frames are matched to `captured_at`: the most recent frame not later than
    the line, within `backfill_tolerance_s`. Existing media is kept unless
    `force` is set. A wanted screenshot with no matching frame -> buffer_miss;
    audio is best-effort until an audio source exists.
    """
    line = get_line_or_404(db, line_id)
    wanted_shot = force or not line.screenshot_path
    wanted_audio = force or not line.audio_path
    if not wanted_shot and not wanted_audio:
        return {"line": LineDTO.from_model(line, _encounter_count(db, line.id)), "updated": False}

    buffer = getattr(request.app.state, "media_buffer", None)
    tolerance = float(settings_store.get(db, "backfill_tolerance_s") or 5.0)
    updated = False
    frame = buffer.frame_at(line.captured_at, tolerance) if (wanted_shot and buffer) else None
    if frame is not None:
        line.screenshot_path = screen.save_screenshot(frame.data, request.app.state.paths)
        updated = True
    if wanted_audio and buffer is not None:
        audio = buffer.audio_at(line.captured_at, tolerance)
        if audio is not None:
            line.audio_path = _save_audio(audio.data, request.app.state.paths)
            updated = True
    if wanted_shot and frame is None:
        raise ApiError("buffer_miss", "缓冲里没有该时间点附近的画面", 404)
    if updated:
        db.commit()
    return {"line": LineDTO.from_model(line, _encounter_count(db, line.id)), "updated": updated}
