"""How much of one work the learner already knows, and what to learn first.

Coverage is counted two ways on purpose: token coverage says how much of the
actual reading is understood, distinct coverage says how many different words
are missing. They answer different questions ("can I enjoy this tonight" vs
"how big is the vocabulary gap").
"""

from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from kotoba.models import Encounter, Line, Term, TermFrequency


def _has_frequency(db: Session) -> bool:
    return db.scalar(select(TermFrequency.id).limit(1)) is not None


def unknown_top(db: Session, source_id: int, limit: int = 50) -> list[dict]:
    """Unknown words of the work, most worth learning first (rank, then count)."""
    counts = (
        select(Encounter.term_id.label("term_id"), func.count(Encounter.id).label("count"))
        .join(Line, Line.id == Encounter.line_id)
        .where(Line.source_id == source_id)
        .group_by(Encounter.term_id)
        .subquery()
    )
    rank = (
        select(func.min(TermFrequency.rank))
        .where(TermFrequency.headword == Term.headword)
        .correlate(Term)
        .scalar_subquery()
    )
    rows = db.execute(
        select(Term, counts.c.count, rank.label("rank"))
        .join(counts, counts.c.term_id == Term.id)
        .where(Term.known_status != "known")
        .order_by(rank.is_(None), rank.asc(), counts.c.count.desc(), Term.id)
        .limit(limit)
    ).all()
    return [
        {
            "term_id": term.id,
            "headword": term.headword,
            "reading": term.reading,
            "rank": int(rank) if rank is not None else None,
            "count": int(count),
        }
        for term, count, rank in rows
    ]


def coverage(db: Session, source_id: int, limit: int = 50) -> dict:
    row = db.execute(
        select(
            func.count(Encounter.id),
            func.count(func.distinct(Encounter.term_id)),
            func.sum(case((Term.known_status == "known", 1), else_=0)),
        )
        .join(Line, Line.id == Encounter.line_id)
        .join(Term, Term.id == Encounter.term_id)
        .where(Line.source_id == source_id)
    ).one()
    total_tokens, distinct_terms, known_tokens = (int(value or 0) for value in row)

    known_terms = int(
        db.scalar(
            select(func.count(func.distinct(Encounter.term_id)))
            .join(Line, Line.id == Encounter.line_id)
            .join(Term, Term.id == Encounter.term_id)
            .where(Line.source_id == source_id, Term.known_status == "known")
        )
        or 0
    )

    return {
        "total_tokens": total_tokens,
        "distinct_terms": distinct_terms,
        "known_tokens": known_tokens,
        "known_terms": known_terms,
        "coverage": known_tokens / total_tokens if total_tokens else 0.0,
        "distinct_coverage": known_terms / distinct_terms if distinct_terms else 0.0,
        "has_frequency": _has_frequency(db),
        "unknown_top": unknown_top(db, source_id, limit),
    }
