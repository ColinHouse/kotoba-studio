"""Line creation shared by the REST router, the capture flow and the hook websocket."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.core.events import broker
from kotoba.models import CaptureSession, Line
from kotoba.schemas import LineCreate, LineDTO
from kotoba.services.jp.normalize import normalize_ocr, text_hash
from kotoba.services.text import dedup


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
                dup.text, dup.raw_text = text, body.raw_text or body.text
                dup.text_hash = text_hash(text)
                dup.tokens_json = None
            if body.screenshot_path and not dup.screenshot_path:
                dup.screenshot_path = body.screenshot_path
            if body.audio_path and not dup.audio_path:
                dup.audio_path = body.audio_path
            db.commit()
            broker.publish(
                {"type": "line.updated", "line": LineDTO.from_model(dup, 0).model_dump(mode="json")}
            )
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
        start_ms=body.start_ms,
        end_ms=body.end_ms,
    )
    db.add(line)
    db.commit()
    broker.publish(
        {"type": "line.created", "line": LineDTO.from_model(line, 0).model_dump(mode="json")}
    )
    return line, False
