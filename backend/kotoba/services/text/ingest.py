"""Line creation shared by the REST router, the capture flow and the hook websocket."""

from __future__ import annotations

import json
from collections.abc import Iterable

from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.core.events import broker
from kotoba.models import CaptureSession, Line
from kotoba.schemas import LineCreate, LineDTO
from kotoba.services.jp.normalize import normalize_ocr, text_hash
from kotoba.services.text import dedup


def create_line(db: Session, body: LineCreate) -> tuple[Line, bool]:
    """Create a line (applying session-level dedup). Returns (line, was_duplicate)."""
    line, duplicate = _stage_line(db, body)
    db.flush()
    event = _event(line, duplicate)
    db.commit()
    broker.publish(event)
    return line, duplicate


def create_lines(db: Session, bodies: Iterable[LineCreate]) -> tuple[int, int]:
    """Create a batch of lines with a single commit; returns (created, skipped).

    Book imports must not pay one commit per sentence, and they only treat an
    exact text hash as a duplicate: the OCR re-capture heuristics would drop a
    long narration sentence that differs from its neighbour by one character.
    """
    created = skipped = 0
    staged: list[tuple[Line, bool]] = []
    for body in bodies:
        line, duplicate = _stage_line(db, body, exact_only=True)
        staged.append((line, duplicate))
        if duplicate:
            skipped += 1
        else:
            created += 1
    db.flush()
    events = [_event(line, duplicate) for line, duplicate in staged]
    db.commit()
    for event in events:
        broker.publish(event)
    return created, skipped


def _stage_line(db: Session, body: LineCreate, exact_only: bool = False) -> tuple[Line, bool]:
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
        dup = dedup.find_duplicate(db, body.session_id, text, exact_only=exact_only)
        if dup is not None:
            if len(text) > len(dup.text):
                dup.text, dup.raw_text = text, body.raw_text or body.text
                dup.text_hash = text_hash(text)
                dup.tokens_json = None
                dup.unknown_count = None
            if body.screenshot_path and not dup.screenshot_path:
                dup.screenshot_path = body.screenshot_path
            if body.audio_path and not dup.audio_path:
                dup.audio_path = body.audio_path
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
        locator_json=json.dumps(body.locator) if body.locator else None,
        ord=body.ord,
        speaker=body.speaker,
        start_ms=body.start_ms,
        end_ms=body.end_ms,
    )
    db.add(line)
    return line, False


def _event(line: Line, duplicate: bool) -> dict:
    event = "line.updated" if duplicate else "line.created"
    return {"type": event, "line": LineDTO.from_model(line, 0).model_dump(mode="json")}
