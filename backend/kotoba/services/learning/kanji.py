"""Kanji-level progress and the difficulty signal of one work.

Words are scattered; kanji have structure. For a Chinese reader the point is
not the characters themselves but the ones outside the jōyō table and the
look-alikes they will misread. One pass over the terms, then per-character
buckets — a grid of 2136 characters must not cost 2136 queries.
"""

from __future__ import annotations

from collections import Counter

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.models import Card, Encounter, Kanji, Line, Term

JOUYOU_MAX_GRADE = 8
STATUSES = ("unseen", "seen", "learning", "mastered")


def _kanji_rows(db: Session) -> dict[str, Kanji]:
    return {row.character: row for row in db.scalars(select(Kanji)).all()}


def _term_rows(db: Session) -> list[tuple[str, str, int]]:
    """(headword, known_status, card count) for every term, in one query."""
    return [
        (headword, status, int(cards))
        for headword, status, cards in db.execute(
            select(Term.headword, Term.known_status, func.count(Card.id))
            .outerjoin(Card, Card.term_id == Term.id)
            .group_by(Term.id)
        ).all()
    ]


def _status(bucket: dict | None) -> str:
    if not bucket or not bucket["terms"]:
        return "unseen"
    if bucket["known"] == bucket["terms"]:
        return "mastered"
    if bucket["cards"] or bucket["known"]:
        return "learning"
    return "seen"


def progress(db: Session) -> dict:
    """Every imported kanji with its term/card counts and mastery bucket."""
    kanji = _kanji_rows(db)
    stats: dict[str, dict] = {}
    for headword, status, cards in _term_rows(db):
        for character in {char for char in headword if char in kanji}:
            bucket = stats.setdefault(character, {"terms": 0, "known": 0, "cards": 0})
            bucket["terms"] += 1
            bucket["cards"] += 1 if cards else 0
            bucket["known"] += 1 if status == "known" else 0

    entries = []
    for character, row in kanji.items():
        bucket = stats.get(character)
        entries.append(
            {
                "character": character,
                "grade": row.grade,
                "jlpt": row.jlpt,
                "stroke_count": row.stroke_count,
                "frequency": row.frequency,
                "terms": bucket["terms"] if bucket else 0,
                "status": _status(bucket),
                "scope": "jouyou" if row.grade and row.grade <= JOUYOU_MAX_GRADE else "other",
            }
        )
    summary = Counter(entry["status"] for entry in entries if entry["scope"] == "jouyou")
    return {
        "installed": bool(kanji),
        "kanji": entries,
        "summary": {
            "total": sum(summary.values()),
            **{status: summary.get(status, 0) for status in STATUSES},
        },
    }


def sort_key(entry: dict) -> tuple:
    """Grid order: jōyō by grade, then newspaper frequency, then codepoint."""
    return (
        entry["grade"] is None,
        entry["grade"] or 0,
        entry["frequency"] or 10**9,
        entry["character"],
    )


def out_of_jouyou(db: Session, source_id: int, limit: int = 200) -> list[dict]:
    """Characters of the work that fall outside the jōyō table, commonest first."""
    rows = db.execute(
        select(Term.headword, func.count(Encounter.id))
        .join(Encounter, Encounter.term_id == Term.id)
        .join(Line, Line.id == Encounter.line_id)
        .where(Line.source_id == source_id)
        .group_by(Term.id)
    ).all()
    kanji = _kanji_rows(db)
    counts: dict[str, dict] = {}
    for headword, occurrences in rows:
        for character in {char for char in headword if char in kanji}:
            row = kanji[character]
            if row.grade and row.grade <= JOUYOU_MAX_GRADE:
                continue
            bucket = counts.setdefault(
                character,
                {
                    "character": character,
                    "grade": row.grade,
                    "stroke_count": row.stroke_count,
                    "occurrences": 0,
                    "terms": 0,
                },
            )
            bucket["occurrences"] += int(occurrences)
            bucket["terms"] += 1
    ordered = sorted(counts.values(), key=lambda item: (-item["occurrences"], item["character"]))
    return ordered[:limit]
