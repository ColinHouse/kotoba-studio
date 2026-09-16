"""i+1 ranking: the most learnable sentence has exactly one unknown word.

All the material is already here — sentences, tokens and known_status — so
counting the unknown content words is what turns the inbox into a study
order. The count ignores particles, symbols and numbers via the existing
`is_content` filter, and words the learner has already met (known, learning
or ignored) do not make a sentence unknown.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from kotoba.models import Line
from kotoba.services.text import analysis as analysis_service

_AWARE_STATUSES = ("known", "learning", "ignored")
SCAN_LIMIT = 500


def unknown_count(db: Session, line: Line) -> int:
    """Distinct content words in the line the learner has not met yet."""
    return len(_unknown_keys(analysis_service.analyze_line(db, line)))


def enrich(db: Session, line: Line) -> int:
    """The cached count, computed and stored once when it is missing."""
    if line.unknown_count is None:
        line.unknown_count = unknown_count(db, line)
        db.flush()
    return line.unknown_count


def sort_key(count: int) -> tuple[int, int]:
    """1 first, then 0, then 2, 3, …; an all-known line is no longer a teaching one."""
    return (0 if count == 1 else 1, count)


def _unknown_keys(analysis: dict) -> set[str]:
    keys: set[str] = set()
    for token in analysis["tokens"]:
        if not token["is_content"] or token["known_status"] in _AWARE_STATUSES:
            continue
        keys.add(token["base"])
    return keys
