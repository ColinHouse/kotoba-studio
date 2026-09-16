"""Detect OCR / hook re-captures of the same line."""

from __future__ import annotations

import difflib

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import Line
from kotoba.services.jp.normalize import normalize_ocr, text_hash

SIMILARITY_THRESHOLD = 0.9


def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, normalize_ocr(a), normalize_ocr(b)).ratio()


def is_growth(previous: str, current: str) -> bool:
    """True when one text is a prefix of the other (typewriter effect / partial OCR)."""
    a, b = normalize_ocr(previous), normalize_ocr(current)
    if not a or not b:
        return False
    return a.startswith(b) or b.startswith(a)


def find_duplicate(db: Session, session_id: int, text: str) -> Line | None:
    """Return an existing line of the session that `text` duplicates, if any.

    Rules: identical normalized hash anywhere in the session; or, against the most
    recent line only, prefix growth or similarity >= SIMILARITY_THRESHOLD.
    """
    h = text_hash(text)
    same = db.scalar(
        select(Line)
        .where(Line.session_id == session_id, Line.text_hash == h)
        .order_by(Line.id.desc())
        .limit(1)
    )
    if same is not None:
        return same
    last = db.scalar(
        select(Line).where(Line.session_id == session_id).order_by(Line.id.desc()).limit(1)
    )
    if last is not None and (
        is_growth(last.text, text) or similarity(last.text, text) >= SIMILARITY_THRESHOLD
    ):
        return last
    return None
