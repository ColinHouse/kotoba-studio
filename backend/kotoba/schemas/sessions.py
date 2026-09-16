"""采集会话 DTO。Capture-session payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from kotoba.models import CaptureSession
from kotoba.schemas.common import SessionMode, TextSource, loads


class SessionCreate(BaseModel):
    source_id: int | None = None
    mode: SessionMode = "quick"
    text_source: TextSource = "ocr"


class SessionDTO(BaseModel):
    id: int
    source_id: int | None
    source_title: str | None = None
    mode: str
    text_source: str
    started_at: datetime
    ended_at: datetime | None
    stats: dict | None
    line_count: int = 0

    @classmethod
    def from_model(cls, s: CaptureSession, line_count: int = 0) -> SessionDTO:
        return cls(
            id=s.id,
            source_id=s.source_id,
            source_title=s.source.title if s.source else None,
            mode=s.mode,
            text_source=s.text_source,
            started_at=s.started_at,
            ended_at=s.ended_at,
            stats=loads(s.stats_json),
            line_count=line_count,
        )


# --- lines -------------------------------------------------------------------
