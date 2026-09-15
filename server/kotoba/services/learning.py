"""Terms, senses, encounters and cards — the learner's own vocabulary."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.errors import ApiError
from kotoba.models import Card, Device, Encounter, Line, Sense, Source, Term
from kotoba.services import settings_store
from kotoba.services.jp import contractions

CARD_TYPES = ("reading", "meaning", "cloze", "listening")
TRAPS_FILE = Path(__file__).resolve().parent.parent / "data" / "homograph_traps_zh.json"


@lru_cache(maxsize=1)
def _traps() -> dict[str, dict]:
    with TRAPS_FILE.open(encoding="utf-8") as fh:
        return {row["headword"]: row for row in json.load(fh)}


def homograph_trap(headword: str) -> dict | None:
    return _traps().get(headword)


def get_or_create_term(
    db: Session,
    headword: str,
    reading: str = "",
    pos: str | None = None,
    jmdict_id: str | None = None,
) -> Term:
    headword = headword.strip()
    reading = (reading or "").strip()
    if not headword:
        raise ApiError("invalid_term", "headword is required")
    term = db.scalar(select(Term).where(Term.headword == headword, Term.reading == reading))
    if term is None:
        term = Term(headword=headword, reading=reading, pos=pos, jmdict_id=jmdict_id)
        db.add(term)
        db.flush()
    else:
        if pos and not term.pos:
            term.pos = pos
        if jmdict_id and not term.jmdict_id:
            term.jmdict_id = jmdict_id
    return term


def ensure_sense(
    db: Session,
    term: Term,
    gloss_zh: str | None,
    gloss_en: str | None,
    origin: str = "jmdict",
) -> Sense | None:
    if not gloss_zh and not gloss_en:
        return None
    for sense in term.senses:
        if sense.gloss_zh == gloss_zh and sense.gloss_en == gloss_en:
            return sense
    sense = Sense(
        term_id=term.id,
        gloss_zh=gloss_zh,
        gloss_en=gloss_en,
        origin=origin,
        ord=len(term.senses),
    )
    db.add(sense)
    db.flush()
    db.refresh(term)
    return sense


def add_encounter(
    db: Session,
    line_id: int,
    headword: str,
    reading: str,
    surface: str,
    span_start: int = 0,
    span_end: int = 0,
    sense: dict | None = None,
    pos: str | None = None,
    jmdict_id: str | None = None,
) -> Encounter:
    line = db.get(Line, line_id)
    if line is None:
        raise ApiError("not_found", f"line {line_id} not found", 404)
    term = get_or_create_term(db, headword, reading, pos=pos, jmdict_id=jmdict_id)
    sense_row = (
        ensure_sense(
            db, term, sense.get("gloss_zh"), sense.get("gloss_en"), sense.get("origin", "jmdict")
        )
        if sense
        else None
    )
    enc = Encounter(
        line_id=line.id,
        term_id=term.id,
        sense_id=sense_row.id if sense_row else None,
        surface=surface or headword,
        span_start=span_start,
        span_end=span_end,
        contraction_of=contractions.expand(surface) if surface else None,
    )
    db.add(enc)
    if line.status == "inbox":
        line.status = "kept"
    db.flush()
    return enc


def default_owner(db: Session) -> str:
    configured = settings_store.get(db, "review_owner_default")
    if configured in ("desktop", "mobile", "any"):
        return configured
    has_mobile = db.scalar(select(Device.id).where(Device.kind == "mobile").limit(1))
    return "mobile" if has_mobile else "desktop"


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
        card = db.scalar(
            select(Card).where(Card.term_id == enc.term_id, Card.card_type == card_type)
        )
        if card is None:
            card = Card(
                term_id=enc.term_id,
                card_type=card_type,
                primary_encounter_id=enc.id,
                review_owner=owner,
            )
            db.add(card)
        elif card.primary_encounter_id is None:
            card.primary_encounter_id = enc.id
        cards.append(card)
    term = db.get(Term, enc.term_id)
    if term is not None and term.known_status == "unknown":
        term.known_status = "learning"
    db.flush()
    return cards


def bulk_set_status(db: Session, headwords: list[str], status: str) -> int:
    if status not in ("unknown", "learning", "known", "ignored"):
        raise ApiError("invalid_status", f"unknown status {status}")
    count = 0
    for headword in dict.fromkeys(h.strip() for h in headwords if h.strip()):
        term = db.scalar(select(Term).where(Term.headword == headword))
        if term is None:
            term = Term(headword=headword, reading="")
            db.add(term)
        term.known_status = status
        count += 1
    db.flush()
    return count


def encounter_timeline(db: Session, term_id: int) -> list[dict]:
    rows = db.execute(
        select(Encounter, Line, Source)
        .join(Line, Line.id == Encounter.line_id)
        .outerjoin(Source, Source.id == Line.source_id)
        .where(Encounter.term_id == term_id)
        .order_by(Line.captured_at.asc(), Encounter.id.asc())
    ).all()
    out = []
    for enc, line, source in rows:
        out.append(
            {
                "id": enc.id,
                "line_id": line.id,
                "term_id": enc.term_id,
                "sense_id": enc.sense_id,
                "surface": enc.surface,
                "span_start": enc.span_start,
                "span_end": enc.span_end,
                "contraction_of": enc.contraction_of,
                "ai_explanation": json.loads(enc.ai_explanation_json)
                if enc.ai_explanation_json
                else None,
                "created_at": enc.created_at.isoformat(),
                "line_text": line.text,
                "screenshot_path": line.screenshot_path,
                "audio_path": line.audio_path,
                "captured_at": line.captured_at.isoformat(),
                "source_id": source.id if source else None,
                "source_title": source.title if source else None,
            }
        )
    return out


def term_summary(db: Session, term: Term) -> dict:
    encounter_count = (
        db.scalar(select(func.count(Encounter.id)).where(Encounter.term_id == term.id)) or 0
    )
    source_count = (
        db.scalar(
            select(func.count(func.distinct(Line.source_id)))
            .join(Encounter, Encounter.line_id == Line.id)
            .where(Encounter.term_id == term.id, Line.source_id.is_not(None))
        )
        or 0
    )
    card_count = db.scalar(select(func.count(Card.id)).where(Card.term_id == term.id)) or 0
    return {
        "id": term.id,
        "headword": term.headword,
        "reading": term.reading,
        "pos": term.pos,
        "jmdict_id": term.jmdict_id,
        "known_status": term.known_status,
        "note": term.note,
        "created_at": term.created_at.isoformat(),
        "senses": [
            {
                "id": s.id,
                "gloss_zh": s.gloss_zh,
                "gloss_en": s.gloss_en,
                "origin": s.origin,
                "ord": s.ord,
            }
            for s in term.senses
        ],
        "encounter_count": encounter_count,
        "source_count": source_count,
        "card_count": card_count,
        "trap": homograph_trap(term.headword),
    }


def term_detail(db: Session, term_id: int) -> dict:
    term = db.get(Term, term_id)
    if term is None:
        raise ApiError("not_found", f"term {term_id} not found", 404)
    detail = term_summary(db, term)
    detail["encounters"] = encounter_timeline(db, term_id)
    detail["cards"] = [card_to_dict(c) for c in term.cards]
    return detail


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


def search_terms(
    db: Session,
    q: str | None = None,
    status: str | None = None,
    source_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[dict]:
    stmt = select(Term).order_by(Term.created_at.desc()).limit(limit).offset(offset)
    if q:
        like = f"%{q}%"
        stmt = stmt.where((Term.headword.like(like)) | (Term.reading.like(like)))
    if status:
        stmt = stmt.where(Term.known_status == status)
    if source_id is not None:
        sub = (
            select(Encounter.term_id)
            .join(Line, Line.id == Encounter.line_id)
            .where(Line.source_id == source_id)
        )
        stmt = stmt.where(Term.id.in_(sub))
    return [term_summary(db, t) for t in db.scalars(stmt).all()]
