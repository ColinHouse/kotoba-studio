"""Pre-study decks: cards from a work's most worth-learning unknown words.

Prestudy happens before playing, so a word may have no context yet; the card
then falls back to word + gloss, and the encounter stays empty. Cards use the
same owner rule as everything else (invariant 3: one card, one owner).
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, Encounter, Term
from kotoba.services.jp import kana
from kotoba.services.learning import coverage
from kotoba.services.learning.cards import default_owner, ensure_card

MAX_LIMIT = 500


def default_types(headword: str) -> list[str]:
    """Same default as the inbox editor: kanji words test the reading first."""
    return ["reading", "cloze"] if kana.has_kanji(headword) else ["meaning", "cloze"]


def cards_for_term(db: Session, term: Term, encounter_id: int | None, owner: str) -> list[Card]:
    cards = [
        ensure_card(db, term.id, card_type, encounter_id, owner)[0]
        for card_type in default_types(term.headword)
    ]
    if term.known_status == "unknown":
        term.known_status = "learning"
    db.flush()
    return cards


def build(db: Session, source_id: int, limit: int = 100) -> dict:
    if limit > MAX_LIMIT:
        raise ApiError("too_many", f"预习一次最多 {MAX_LIMIT} 个词")
    owner = default_owner(db)
    created = skipped = 0
    for row in coverage.unknown_top(db, source_id, limit):
        term = db.get(Term, row["term_id"])
        has_card = db.scalar(select(Card.id).where(Card.term_id == term.id).limit(1))
        if has_card is not None:
            skipped += 1
            continue
        encounter_id = db.scalar(
            select(Encounter.id).where(Encounter.term_id == term.id).order_by(Encounter.id).limit(1)
        )
        cards_for_term(db, term, encounter_id, owner)
        created += 1
    return {"created": created, "skipped": skipped}
