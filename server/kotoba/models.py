"""ORM models. See docs/superpowers/specs/2026-09-15-kotoba-studio-design.md §4."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(UTC)


class UTCDateTime(TypeDecorator):
    """Store timezone-aware datetimes as naive UTC in SQLite and restore tzinfo on load."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if value.tzinfo is not None:
            value = value.astimezone(UTC).replace(tzinfo=None)
        return value

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        return value.replace(tzinfo=UTC)


class Base(DeclarativeBase):
    pass


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
    encounters: Mapped[list[Encounter]] = relationship(back_populates="line")


class Term(Base):
    __tablename__ = "terms"
    __table_args__ = (UniqueConstraint("headword", "reading", name="uq_terms_headword_reading"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    headword: Mapped[str] = mapped_column(String(100), index=True)
    reading: Mapped[str] = mapped_column(String(100), default="")
    pos: Mapped[str | None] = mapped_column(String(40))
    jmdict_id: Mapped[str | None] = mapped_column(String(20))
    known_status: Mapped[str] = mapped_column(String(16), default="unknown", index=True)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    senses: Mapped[list[Sense]] = relationship(back_populates="term", order_by="Sense.ord")
    encounters: Mapped[list[Encounter]] = relationship(back_populates="term")
    cards: Mapped[list[Card]] = relationship(back_populates="term")


class Sense(Base):
    __tablename__ = "senses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), index=True)
    gloss_zh: Mapped[str | None] = mapped_column(Text)
    gloss_en: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(String(16), default="jmdict")
    ord: Mapped[int] = mapped_column(Integer, default=0)

    term: Mapped[Term] = relationship(back_populates="senses")


class Encounter(Base):
    __tablename__ = "encounters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    line_id: Mapped[int] = mapped_column(ForeignKey("lines.id", ondelete="CASCADE"), index=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), index=True)
    sense_id: Mapped[int | None] = mapped_column(ForeignKey("senses.id", ondelete="SET NULL"))
    surface: Mapped[str] = mapped_column(String(100))
    span_start: Mapped[int] = mapped_column(Integer, default=0)
    span_end: Mapped[int] = mapped_column(Integer, default=0)
    contraction_of: Mapped[str | None] = mapped_column(String(100))
    ai_explanation_json: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    line: Mapped[Line] = relationship(back_populates="encounters")
    term: Mapped[Term] = relationship(back_populates="encounters")
    sense: Mapped[Sense | None] = relationship()


class Card(Base):
    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("term_id", "card_type", name="uq_cards_term_type"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    term_id: Mapped[int] = mapped_column(ForeignKey("terms.id", ondelete="CASCADE"), index=True)
    card_type: Mapped[str] = mapped_column(String(16))
    primary_encounter_id: Mapped[int | None] = mapped_column(
        ForeignKey("encounters.id", ondelete="SET NULL")
    )
    review_owner: Mapped[str] = mapped_column(String(16), default="desktop", index=True)
    suspended: Mapped[bool] = mapped_column(Boolean, default=False)
    fsrs_state: Mapped[int] = mapped_column(Integer, default=1)
    fsrs_step: Mapped[int | None] = mapped_column(Integer)
    stability: Mapped[float | None] = mapped_column(Float)
    difficulty: Mapped[float | None] = mapped_column(Float)
    due: Mapped[datetime | None] = mapped_column(UTCDateTime, index=True)
    last_review: Mapped[datetime | None] = mapped_column(UTCDateTime)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    term: Mapped[Term] = relationship(back_populates="cards")
    primary_encounter: Mapped[Encounter | None] = relationship()


class ReviewLog(Base):
    __tablename__ = "review_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    card_id: Mapped[int] = mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    mode: Mapped[str] = mapped_column(String(16), default="scheduled", index=True)
    reviewed_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    device_id: Mapped[str | None] = mapped_column(String(64))
    session_id: Mapped[int | None] = mapped_column(ForeignKey("sessions.id", ondelete="SET NULL"))


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(16), default="desktop")
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    last_seen: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Dictionary(Base):
    __tablename__ = "dictionaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[str | None] = mapped_column(String(100))
    kind: Mapped[str] = mapped_column(String(16), default="jmdict")
    entry_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class DictEntry(Base):
    __tablename__ = "dict_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dict_id: Mapped[int] = mapped_column(
        ForeignKey("dictionaries.id", ondelete="CASCADE"), index=True
    )
    ext_id: Mapped[str] = mapped_column(String(40), index=True)
    senses_json: Mapped[str] = mapped_column(Text)
    pos_json: Mapped[str | None] = mapped_column(Text)
    common: Mapped[bool] = mapped_column(Boolean, default=False)
    is_expression: Mapped[bool] = mapped_column(Boolean, default=False)

    forms: Mapped[list[DictForm]] = relationship(back_populates="entry")


class DictForm(Base):
    __tablename__ = "dict_forms"
    __table_args__ = (Index("ix_dict_forms_text_kind", "text", "kind"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("dict_entries.id", ondelete="CASCADE"), index=True
    )
    text: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(8))
    common: Mapped[bool] = mapped_column(Boolean, default=False)

    entry: Mapped[DictEntry] = relationship(back_populates="forms")


class LlmCall(Base):
    __tablename__ = "llm_calls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    purpose: Mapped[str] = mapped_column(String(32))
    model: Mapped[str] = mapped_column(String(64))
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    cost_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    ok: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value_json: Mapped[str] = mapped_column(Text)
