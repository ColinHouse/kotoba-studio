"""Colloquial contractions (口语缩约) → canonical forms."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "jp_contractions.json"


@lru_cache(maxsize=1)
def load() -> dict[str, dict]:
    with DATA_FILE.open(encoding="utf-8") as fh:
        rows = json.load(fh)
    return {row["form"]: row for row in rows}


def expand(surface: str) -> str | None:
    """Return the canonical form of a contraction, or None if `surface` is not one."""
    row = load().get(surface)
    return row["full"] if row else None


def find_in(text: str) -> list[dict]:
    """All contraction rows whose form occurs in `text` (longest forms first)."""
    rows = sorted(load().values(), key=lambda r: -len(r["form"]))
    return [r for r in rows if r["form"] in text]


def find_in_tokens(surfaces: list[str], max_len: int = 4) -> list[dict]:
    """Contractions aligned to token boundaries: a form must equal one token surface or the
    concatenation of consecutive surfaces. Avoids matching って inside 奢って."""
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
