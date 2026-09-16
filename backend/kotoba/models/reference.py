"""词典数据：已安装词典及其词条与写法。Installed dictionaries, entries and written forms."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kotoba.models.base import Base, UTCDateTime, utcnow


class Dictionary(Base):
    __tablename__ = "dictionaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    revision: Mapped[str | None] = mapped_column(String(100))
    author: Mapped[str | None] = mapped_column(String(200))
    attribution: Mapped[str | None] = mapped_column(Text)
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

    forms: Mapped[list[DictForm]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", passive_deletes=True
    )


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


class TermFrequency(Base):
    """A word's rank in one frequency dictionary; `reading` NULL means any reading."""

    __tablename__ = "term_frequencies"
    __table_args__ = (
        UniqueConstraint("dict_id", "headword", "reading", name="uq_term_frequencies"),
        Index("ix_term_frequencies_headword", "headword"),
        Index("ix_term_frequencies_headword_reading", "headword", "reading"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dict_id: Mapped[int] = mapped_column(
        ForeignKey("dictionaries.id", ondelete="CASCADE"), index=True
    )
    headword: Mapped[str] = mapped_column(String(200))
    reading: Mapped[str | None] = mapped_column(String(200))
    rank: Mapped[int] = mapped_column(Integer)


class TermPitch(Base):
    """Pitch accent of a word; `accent` is the downstep mora, 0 = heiban."""

    __tablename__ = "term_pitches"
    __table_args__ = (UniqueConstraint("headword", "reading", "accent", name="uq_term_pitches"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    headword: Mapped[str] = mapped_column(String(200), index=True)
    reading: Mapped[str] = mapped_column(String(200))
    accent: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(40), default="kanjium")
