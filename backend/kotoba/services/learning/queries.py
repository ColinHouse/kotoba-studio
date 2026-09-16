"""词库读取：时间线、摘要与检索。Read models for the library views."""

from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, Encounter, Line, Source, Term, TermFrequency
from kotoba.services.dictionary.yomitan import frequency
from kotoba.services.learning.cards import card_to_dict
from kotoba.services.learning.traps import homograph_trap


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
        "frequency_rank": frequency.rank_for(db, term.headword, term.reading),
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


def search_terms(
    db: Session,
    q: str | None = None,
    status: str | None = None,
    source_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    sort: str = "recent",
) -> list[dict]:
    stmt = select(Term).limit(limit).offset(offset)
    if sort == "frequency":
        # The most common word first; words without any rank come last, not first.
        rank = (
            select(func.min(TermFrequency.rank))
            .where(TermFrequency.headword == Term.headword)
            .correlate(Term)
            .scalar_subquery()
        )
        stmt = stmt.order_by(rank.is_(None), rank.asc(), Term.created_at.desc())
    else:
        stmt = stmt.order_by(Term.created_at.desc())
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
