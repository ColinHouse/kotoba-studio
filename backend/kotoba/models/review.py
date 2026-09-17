"""复习：卡片、复习记录、设备。Cards, review logs and registered devices."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from kotoba.models.base import Base, UTCDateTime, utcnow

if TYPE_CHECKING:
    from kotoba.models.vocabulary import Encounter, Term


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
    client_id: Mapped[str | None] = mapped_column(String(36), unique=True, index=True)
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
