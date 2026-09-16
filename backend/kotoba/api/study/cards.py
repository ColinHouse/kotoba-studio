"""Cards (可复习单位)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import Card
from kotoba.services import learning

router = APIRouter(prefix="/cards", tags=["cards"])


class CardsCreate(BaseModel):
    encounter_id: int
    card_types: list[str]
    owner: Literal["desktop", "mobile", "any"] | None = None


class CardUpdate(BaseModel):
    review_owner: Literal["desktop", "mobile", "any"] | None = None
    suspended: bool | None = None
    primary_encounter_id: int | None = None


@router.post("", status_code=201)
def create_cards(body: CardsCreate, db: Session = Depends(get_db)) -> list[dict]:
    cards = learning.create_cards(db, body.encounter_id, body.card_types, body.owner)
    db.commit()
    return [learning.card_to_dict(c) for c in cards]


@router.get("")
def list_cards(
    term_id: int | None = None,
    owner: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
) -> list[dict]:
    stmt = select(Card).order_by(Card.created_at.desc()).limit(limit)
    if term_id is not None:
        stmt = stmt.where(Card.term_id == term_id)
    if owner is not None:
        stmt = stmt.where(Card.review_owner == owner)
    return [learning.card_to_dict(c) for c in db.scalars(stmt).all()]


@router.get("/stats")
def card_stats(db: Session = Depends(get_db)) -> dict:
    now = datetime.now(UTC)
    total = db.scalar(select(func.count(Card.id))) or 0
    new = db.scalar(select(func.count(Card.id)).where(Card.due.is_(None))) or 0
    due = (
        db.scalar(
            select(func.count(Card.id)).where(
                Card.due.is_not(None), Card.due <= now, Card.suspended.is_(False)
            )
        )
        or 0
    )
    by_owner = dict(
        db.execute(select(Card.review_owner, func.count(Card.id)).group_by(Card.review_owner)).all()
    )
    by_state = dict(
        db.execute(select(Card.fsrs_state, func.count(Card.id)).group_by(Card.fsrs_state)).all()
    )
    return {
        "total": total,
        "new": new,
        "due_now": due,
        "by_owner": by_owner,
        "by_state": {str(k): v for k, v in by_state.items()},
    }


@router.patch("/{card_id}")
def update_card(card_id: int, body: CardUpdate, db: Session = Depends(get_db)) -> dict:
    card = db.get(Card, card_id)
    if card is None:
        raise ApiError("not_found", f"card {card_id} not found", 404)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(card, key, value)
    db.commit()
    return learning.card_to_dict(card)
