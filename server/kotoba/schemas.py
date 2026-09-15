"""Pydantic DTOs shared by the API routers."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from kotoba.models import CaptureSession, Line, Source

Kind = Literal["game", "anime", "video", "manga", "other"]
LineStatus = Literal["inbox", "kept", "discarded"]


def _loads(s: str | None) -> Any:
    return json.loads(s) if s else None


# --- sources -----------------------------------------------------------------


class SourceCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    title_ja: str | None = None
    kind: Kind = "game"
    region: dict | None = None


class SourceUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    title_ja: str | None = None
    kind: Kind | None = None
    region: dict | None = None


class SourceDTO(BaseModel):
    id: int
    title: str
    title_ja: str | None
    kind: str
    region: dict | None
    created_at: datetime
    line_count: int = 0
    term_count: int = 0

    @classmethod
    def from_model(cls, s: Source, line_count: int = 0, term_count: int = 0) -> SourceDTO:
        return cls(
            id=s.id,
            title=s.title,
            title_ja=s.title_ja,
            kind=s.kind,
            region=_loads(s.region_json),
            created_at=s.created_at,
            line_count=line_count,
            term_count=term_count,
        )


# --- sessions ----------------------------------------------------------------


class SessionCreate(BaseModel):
    source_id: int | None = None
    mode: Literal["quick", "companion", "import"] = "quick"
    text_source: Literal["ocr", "hook", "subtitle", "manual"] = "ocr"


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
            stats=_loads(s.stats_json),
            line_count=line_count,
        )


# --- lines -------------------------------------------------------------------


class LineCreate(BaseModel):
    text: str = Field(min_length=1)
    session_id: int | None = None
    source_id: int | None = None
    raw_text: str | None = None
    origin: Literal["manual", "hook", "ocr", "subtitle"] = "manual"
    screenshot_path: str | None = None
    audio_path: str | None = None
    position: dict | None = None
    speaker: str | None = None


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
    speaker: str | None
    translation_zh: str | None
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
            position=_loads(line.position_json),
            speaker=line.speaker,
            translation_zh=line.translation_zh,
            status=line.status,
            captured_at=line.captured_at,
            encounter_count=encounter_count,
        )


class LineCreated(BaseModel):
    line: LineDTO
    duplicate: bool = False
