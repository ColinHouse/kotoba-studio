"""FSRS scheduling on top of py-fsrs, with device ownership and quiz isolation."""

from __future__ import annotations

from datetime import datetime

from fsrs import Card as FsrsCard
from fsrs import Rating, Scheduler, State
from sqlalchemy import case, select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, ReviewLog, utcnow
from kotoba.services import settings_store

MODES = ("scheduled", "session_quiz")


def scheduler(db: Session) -> Scheduler:
    retention = float(settings_store.get(db, "desired_retention") or 0.9)
    parameters = settings_store.get(db, "fsrs_parameters")
    if parameters:
        return Scheduler(parameters=parameters, desired_retention=retention)
    return Scheduler(desired_retention=retention)


def to_fsrs_card(card: Card, now: datetime | None = None) -> FsrsCard:
    return FsrsCard(
        card_id=card.id,
        state=State(card.fsrs_state or 1),
        step=card.fsrs_step,
        stability=card.stability,
        difficulty=card.difficulty,
        due=card.due or now or utcnow(),
        last_review=card.last_review,
    )


def apply_fsrs_card(card: Card, fc: FsrsCard) -> None:
    card.fsrs_state = fc.state.value
    card.fsrs_step = fc.step
    card.stability = fc.stability
    card.difficulty = fc.difficulty
    card.due = fc.due
    card.last_review = fc.last_review


def review(
    db: Session,
    card: Card,
    rating: int,
    mode: str = "scheduled",
    device_id: str | None = None,
    now: datetime | None = None,
    duration_ms: int | None = None,
    session_id: int | None = None,
) -> Card:
    """Record a review. Only mode == "scheduled" changes the FSRS state."""
    if mode not in MODES:
        raise ApiError("invalid_mode", f"mode must be one of {MODES}")
    if rating not in (1, 2, 3, 4):
        raise ApiError("invalid_rating", "rating must be 1 (Again) … 4 (Easy)")
    now = now or utcnow()
    if mode == "scheduled":
        fc = to_fsrs_card(card, now)
        duration_s = int(duration_ms / 1000) if duration_ms else None
        new_fc, _log = scheduler(db).review_card(
            fc, Rating(rating), review_datetime=now, review_duration=duration_s
        )
        apply_fsrs_card(card, new_fc)
    db.add(
        ReviewLog(
            card_id=card.id,
            rating=rating,
            mode=mode,
            reviewed_at=now,
            duration_ms=duration_ms,
            device_id=device_id,
            session_id=session_id,
        )
    )
    db.flush()
    return card


def preview(db: Session, card: Card, now: datetime | None = None) -> dict[str, str]:
    """Due dates that each rating would produce (never persisted)."""
    now = now or utcnow()
    sched = scheduler(db)
    out: dict[str, str] = {}
    for rating in Rating:
        fc, _ = sched.review_card(to_fsrs_card(card, now), rating, review_datetime=now)
        out[rating.name.lower()] = fc.due.isoformat()
    return out


def queue(
    db: Session,
    device_kind: str,
    limit: int = 20,
    now: datetime | None = None,
    include_new: bool = True,
) -> list[Card]:
    """Due cards this device is allowed to review: overdue first, then new."""
    now = now or utcnow()
    stmt = (
        select(Card)
        .where(
            Card.review_owner.in_([device_kind, "any"]),
            Card.suspended.is_(False),
        )
        .order_by(case((Card.due.is_(None), 1), else_=0), Card.due.asc(), Card.id.asc())
        .limit(limit)
    )
    if include_new:
        stmt = stmt.where((Card.due.is_(None)) | (Card.due <= now))
    else:
        stmt = stmt.where(Card.due.is_not(None), Card.due <= now)
    return list(db.scalars(stmt).all())


def retrievability(db: Session, card: Card, now: datetime | None = None) -> float:
    if card.due is None or card.stability is None:
        return 0.0
    return float(scheduler(db).get_card_retrievability(to_fsrs_card(card, now), now or utcnow()))
