"""作品 DTO。Source payloads."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from kotoba.models import Source
from kotoba.schemas.common import Kind, loads


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
            region=loads(s.region_json),
            created_at=s.created_at,
            line_count=line_count,
            term_count=term_count,
        )


# --- sessions ----------------------------------------------------------------
