"""词汇：词条、义项、语境。Terms, senses and the encounters that link them to lines."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kotoba.models.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from kotoba.models.capture import Line
    from kotoba.models.review import Card


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

    senses: Mapped[list[Sense]] = relationship(
        back_populates="term",
        order_by="Sense.ord",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    encounters: Mapped[list[Encounter]] = relationship(
        back_populates="term", cascade="all, delete-orphan", passive_deletes=True
    )
    cards: Mapped[list[Card]] = relationship(
        back_populates="term", cascade="all, delete-orphan", passive_deletes=True
    )


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
