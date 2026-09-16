"""词条与语境的写入。Creating terms, senses and encounters."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Encounter, Line, Sense, Term
from kotoba.services.jp import contractions


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
