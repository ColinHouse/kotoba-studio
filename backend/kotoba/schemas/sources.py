"""作品 DTO。Source payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from kotoba.models import Source
from kotoba.schemas.common import Kind, loads


class WindowBinding(BaseModel):
    """The game window a work is played in, with a dialogue box relative to its client area."""

    process: str = Field(min_length=1, max_length=120)
    title: str | None = Field(default=None, max_length=200)
    region: dict | None = None


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
    window: WindowBinding | None = None


class SourceDTO(BaseModel):
    id: int
    title: str
    title_ja: str | None
    kind: str
    region: dict | None
    window: dict | None
    created_at: datetime
    line_count: int = 0
    term_count: int = 0
    known_term_count: int = 0

    @classmethod
    def from_model(
        cls, s: Source, line_count: int = 0, term_count: int = 0, known_term_count: int = 0
    ) -> SourceDTO:
        return cls(
            id=s.id,
            title=s.title,
            title_ja=s.title_ja,
            kind=s.kind,
            region=loads(s.region_json),
            window=loads(s.window_json),
            created_at=s.created_at,
            line_count=line_count,
            term_count=term_count,
            known_term_count=known_term_count,
        )


# --- sessions ----------------------------------------------------------------
