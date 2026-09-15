"""Post-session summary (会后复盘)."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.errors import ApiError
from kotoba.models import CaptureSession, Card, Encounter, Line, ReviewLog, Term, utcnow


def session_summary(db: Session, session_id: int) -> dict:
    session = db.get(CaptureSession, session_id)
    if session is None:
        raise ApiError("not_found", f"session {session_id} not found", 404)
    counts = dict(
        db.execute(
            select(Line.status, func.count(Line.id))
            .where(Line.session_id == session_id)
            .group_by(Line.status)
        ).all()
    )
    session_lines = select(Line.id).where(Line.session_id == session_id)
    term_ids = set(
        db.scalars(
            select(Encounter.term_id).where(Encounter.line_id.in_(session_lines)).distinct()
        ).all()
    )
    new_terms: list[dict] = []
    seen_again: list[dict] = []
    for term_id in term_ids:
        earlier = db.scalar(
            select(func.count(Encounter.id))
            .join(Line, Line.id == Encounter.line_id)
            .where(Encounter.term_id == term_id, Line.session_id != session_id)
        )
        term = db.get(Term, term_id)
        entry = {"id": term.id, "headword": term.headword, "reading": term.reading}
        (seen_again if earlier else new_terms).append(entry)
    cards_created = (
        db.scalar(
            select(func.count(Card.id))
            .join(Encounter, Encounter.id == Card.primary_encounter_id)
            .where(Encounter.line_id.in_(session_lines))
        )
        or 0
    )
    quiz_rows = db.execute(
        select(ReviewLog.rating, func.count(ReviewLog.id))
        .where(ReviewLog.session_id == session_id, ReviewLog.mode == "session_quiz")
        .group_by(ReviewLog.rating)
    ).all()
    answered = sum(c for _, c in quiz_rows)
    correct = sum(c for r, c in quiz_rows if r >= 3)
    ended = session.ended_at or utcnow()
    return {
        "session_id": session_id,
        "source_id": session.source_id,
        "started_at": session.started_at.isoformat(),
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration_s": int((ended - session.started_at).total_seconds()),
        "lines_total": sum(counts.values()),
        "kept": counts.get("kept", 0),
        "inbox": counts.get("inbox", 0),
        "discarded": counts.get("discarded", 0),
        "new_terms": new_terms,
        "seen_again_terms": seen_again,
        "cards_created": cards_created,
        "quiz": {"answered": answered, "correct": correct},
    }
