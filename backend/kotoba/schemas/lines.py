"""台词 DTO。Captured-line payloads."""

from __future__ import annotations

import json
from datetime import datetime

from pydantic import BaseModel, Field

from kotoba.models import Line
from kotoba.schemas.common import LineOrigin, LineStatus, loads


def line_locator(line: Line) -> dict | None:
    """Where the line sits in its work, reading old fields when locator_json is absent."""
    if line.locator_json:
        try:
            data = json.loads(line.locator_json)
        except json.JSONDecodeError:
            data = None
        if isinstance(data, dict) and data.get("kind"):
            return data
    if line.start_ms is not None or line.end_ms is not None:
        return {"kind": "time", "start_ms": line.start_ms, "end_ms": line.end_ms}
    position = loads(line.position_json)
    if isinstance(position, dict) and position.get("region"):
        return {"kind": "region", "region": position["region"]}
    return None


class LineCreate(BaseModel):
    text: str = Field(min_length=1)
    session_id: int | None = None
    source_id: int | None = None
    raw_text: str | None = None
    origin: LineOrigin = "manual"
    screenshot_path: str | None = None
    audio_path: str | None = None
    position: dict | None = None
    locator: dict | None = None
    ord: int | None = None
    speaker: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None


class LineUpdate(BaseModel):
    text: str | None = Field(default=None, min_length=1)
    status: LineStatus | None = None
    speaker: str | None = None
    translation_zh: str | None = None


class LineDTO(BaseModel):
    id: int
    session_id: int | None
    source_id: int | None
    text: str
    raw_text: str | None
    origin: str
    screenshot_path: str | None
    audio_path: str | None
    position: dict | None
    locator: dict | None
    ord: int | None
    speaker: str | None
    start_ms: int | None
    end_ms: int | None
    translation_zh: str | None
    unknown_count: int | None
    status: str
    captured_at: datetime
    encounter_count: int = 0

    @classmethod
    def from_model(cls, line: Line, encounter_count: int | None = None) -> LineDTO:
        if encounter_count is None:
            encounter_count = len(line.encounters) if "encounters" in line.__dict__ else 0
        return cls(
            id=line.id,
            session_id=line.session_id,
            source_id=line.source_id,
            text=line.text,
            raw_text=line.raw_text,
            origin=line.origin,
            screenshot_path=line.screenshot_path,
            audio_path=line.audio_path,
            position=loads(line.position_json),
            locator=line_locator(line),
            ord=line.ord,
            speaker=line.speaker,
            start_ms=line.start_ms,
            end_ms=line.end_ms,
            translation_zh=line.translation_zh,
            unknown_count=line.unknown_count,
            status=line.status,
            captured_at=line.captured_at,
            encounter_count=encounter_count,
        )


class LineCreated(BaseModel):
    line: LineDTO
    duplicate: bool = False
