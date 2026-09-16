"""采集：作品、会话、句子。Sources, capture sessions and captured lines."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kotoba.models.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from kotoba.models.vocabulary import Encounter


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), default="game")
    title: Mapped[str] = mapped_column(String(200))
    title_ja: Mapped[str | None] = mapped_column(String(200))
    region_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class CaptureSession(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    mode: Mapped[str] = mapped_column(String(16), default="quick")
    text_source: Mapped[str] = mapped_column(String(16), default="ocr")
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime)
    stats_json: Mapped[str | None] = mapped_column(Text)

    source: Mapped[Source | None] = relationship()


class Line(Base):
    __tablename__ = "lines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"))
    source_id: Mapped[int | None] = mapped_column(ForeignKey("sources.id", ondelete="SET NULL"))
    text: Mapped[str] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    text_hash: Mapped[str] = mapped_column(String(40), index=True)
    origin: Mapped[str] = mapped_column(String(16), default="manual")
    screenshot_path: Mapped[str | None] = mapped_column(String(300))
    audio_path: Mapped[str | None] = mapped_column(String(300))
    position_json: Mapped[str | None] = mapped_column(Text)
    speaker: Mapped[str | None] = mapped_column(String(100))
    translation_zh: Mapped[str | None] = mapped_column(Text)
    tokens_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(16), default="inbox", index=True)
    captured_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)

    session: Mapped[CaptureSession | None] = relationship()
    source: Mapped[Source | None] = relationship()
    encounters: Mapped[list[Encounter]] = relationship(
        back_populates="line", cascade="all, delete-orphan", passive_deletes=True
    )
