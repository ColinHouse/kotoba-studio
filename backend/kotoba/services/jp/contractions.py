"""口语缩约还原。Colloquial contractions mapped back to their canonical forms.

Matching is done on token boundaries, not raw substrings: って inside 奢って is the
te-form, not the quotative particle.
"""

from __future__ import annotations

from functools import lru_cache

from kotoba.core.resources import CONTRACTIONS_FILE, load_json


@lru_cache(maxsize=1)
def load() -> dict[str, dict]:
    return {row["form"]: row for row in load_json(CONTRACTIONS_FILE)}


def expand(surface: str) -> str | None:
    """Return the canonical form of a contraction, or None if `surface` is not one."""
    row = load().get(surface)
    return row["full"] if row else None


def find_in(text: str) -> list[dict]:
    """All contraction rows whose form occurs anywhere in `text` (longest first)."""
    rows = sorted(load().values(), key=lambda r: -len(r["form"]))
    return [r for r in rows if r["form"] in text]


def find_in_tokens(surfaces: list[str], max_len: int = 4) -> list[dict]:
    """Contractions aligned to token boundaries.

    A form must equal one token surface or the concatenation of consecutive
    surfaces, which keeps って inside 奢って from matching the quotative particle.
    """
    table = load()
    found: list[dict] = []
    seen: set[str] = set()
    for i in range(len(surfaces)):
        run = ""
        for j in range(i, min(i + max_len, len(surfaces))):
            run += surfaces[j]
            row = table.get(run)
            if row and row["form"] not in seen:
                seen.add(row["form"])
                found.append(row)
    return found
