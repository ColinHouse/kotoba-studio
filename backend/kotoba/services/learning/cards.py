"""卡片的创建与序列化。Creating review cards and rendering them as JSON."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, Device, Encounter, Term
from kotoba.services import settings_store

CARD_TYPES = ("reading", "meaning", "cloze", "listening")


def default_owner(db: Session) -> str:
    configured = settings_store.get(db, "review_owner_default")
    if configured in ("desktop", "mobile", "any"):
        return configured
    has_mobile = db.scalar(select(Device.id).where(Device.kind == "mobile").limit(1))
    return "mobile" if has_mobile else "desktop"


def ensure_card(
    db: Session,
    term_id: int,
    card_type: str,
    encounter_id: int | None,
    owner: str,
) -> tuple[Card, bool]:
    """Find or create one card; returns (card, was_created). Encounter may be None."""
    card = db.scalar(select(Card).where(Card.term_id == term_id, Card.card_type == card_type))
    if card is not None:
        if encounter_id is not None and card.primary_encounter_id is None:
            card.primary_encounter_id = encounter_id
        return card, False
    card = Card(
        term_id=term_id,
        card_type=card_type,
        primary_encounter_id=encounter_id,
        review_owner=owner,
    )
    db.add(card)
    return card, True


def create_cards(
    db: Session, encounter_id: int, card_types: list[str], owner: str | None = None
) -> list[Card]:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise ApiError("not_found", f"encounter {encounter_id} not found", 404)
    bad = [t for t in card_types if t not in CARD_TYPES]
    if bad:
        raise ApiError("invalid_card_type", f"unknown card type(s): {', '.join(bad)}")
    owner = owner or default_owner(db)
    cards: list[Card] = []
    for card_type in dict.fromkeys(card_types):
        card, _ = ensure_card(db, enc.term_id, card_type, enc.id, owner)
        cards.append(card)
    term = db.get(Term, enc.term_id)
    if term is not None and term.known_status == "unknown":
        term.known_status = "learning"
    db.flush()
    return cards


def card_to_dict(card: Card) -> dict:
    return {
        "id": card.id,
        "term_id": card.term_id,
        "card_type": card.card_type,
        "primary_encounter_id": card.primary_encounter_id,
        "review_owner": card.review_owner,
        "suspended": card.suspended,
        "state": card.fsrs_state,
        "step": card.fsrs_step,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": card.due.isoformat() if card.due else None,
        "last_review": card.last_review.isoformat() if card.last_review else None,
        "created_at": card.created_at.isoformat(),
        "headword": card.term.headword if card.term else None,
        "reading": card.term.reading if card.term else None,
    }
