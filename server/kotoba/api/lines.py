"""Captured lines (台词) and their analysis."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import CaptureSession, Encounter, Line
from kotoba.schemas import LineCreate, LineCreated, LineDTO, LineUpdate
from kotoba.services import analysis, dedup
from kotoba.services.events import broker
from kotoba.services.jp.normalize import normalize_ocr, text_hash

router = APIRouter(prefix="/lines", tags=["lines"])


def get_line_or_404(db: Session, line_id: int) -> Line:
    line = db.get(Line, line_id)
    if line is None:
        raise ApiError("not_found", f"line {line_id} not found", 404)
    return line


def _encounter_count(db: Session, line_id: int) -> int:
    return db.scalar(select(func.count(Encounter.id)).where(Encounter.line_id == line_id)) or 0


def create_line(db: Session, body: LineCreate) -> tuple[Line, bool]:
    """Create a line (applying session-level dedup). Returns (line, was_duplicate)."""
    text = normalize_ocr(body.text)
    if not text:
        raise ApiError("empty_text", "text is empty after normalization")
    source_id = body.source_id
    if body.session_id is not None:
        session = db.get(CaptureSession, body.session_id)
        if session is None:
            raise ApiError("not_found", f"session {body.session_id} not found", 404)
        if source_id is None:
            source_id = session.source_id
        dup = dedup.find_duplicate(db, body.session_id, text)
        if dup is not None:
            if len(text) > len(dup.text):
                dup.text, dup.raw_text, dup.text_hash = (
                    text,
                    body.raw_text or body.text,
                    text_hash(text),
                )
                dup.tokens_json = None
            if body.screenshot_path and not dup.screenshot_path:
                dup.screenshot_path = body.screenshot_path
            db.commit()
            return dup, True
    line = Line(
        session_id=body.session_id,
        source_id=source_id,
        text=text,
        raw_text=body.raw_text or body.text,
        text_hash=text_hash(text),
        origin=body.origin,
        screenshot_path=body.screenshot_path,
        audio_path=body.audio_path,
        position_json=json.dumps(body.position) if body.position else None,
        speaker=body.speaker,
    )
    db.add(line)
    db.commit()
    broker.publish(
        {"type": "line.created", "line": LineDTO.from_model(line, 0).model_dump(mode="json")}
    )
    return line, False


@router.get("")
def list_lines(
    session_id: int | None = None,
    source_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[LineDTO]:
    stmt = (
        select(Line).order_by(Line.captured_at.desc(), Line.id.desc()).limit(limit).offset(offset)
    )
    if session_id is not None:
        stmt = stmt.where(Line.session_id == session_id)
    if source_id is not None:
        stmt = stmt.where(Line.source_id == source_id)
    if status is not None:
        stmt = stmt.where(Line.status == status)
    return [
        LineDTO.from_model(line, _encounter_count(db, line.id)) for line in db.scalars(stmt).all()
    ]


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
