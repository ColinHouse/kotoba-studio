"""Group consecutive tokens into dictionary expressions (e.g. しょう+が+ない → しょうがない)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import DictEntry, DictForm, Dictionary
from kotoba.services.jp.kana import to_hiragana
from kotoba.services.jp.tokenizer import Token

ReadingLookup = Callable[[str], set[str] | None]


@dataclass(slots=True)
class Span:
    start_tok: int
    end_tok: int  # inclusive
    text: str
    matched_form: str
    reading: str

    def to_dict(self) -> dict:
        return asdict(self)


def group(tokens: list[Token], readings_for: ReadingLookup, max_len: int = 6) -> list[Span]:
    """Greedy longest match; a match must agree on both written form and reading."""
    spans: list[Span] = []
    i, n = 0, len(tokens)
    while i < n:
        found: Span | None = None
        for length in range(min(max_len, n - i), 1, -1):
            seg = tokens[i : i + length]
            surface = "".join(t.surface for t in seg)
            surface_reading = to_hiragana("".join(t.reading for t in seg))
            base_form = "".join(t.surface for t in seg[:-1]) + seg[-1].base
            base_reading = to_hiragana("".join(t.reading for t in seg[:-1]) + seg[-1].reading_base)
            for form, reading in ((surface, surface_reading), (base_form, base_reading)):
                readings = readings_for(form)
                if readings is None:
                    continue
                if reading in readings or to_hiragana(form) in readings:
                    found = Span(i, i + length - 1, surface, form, reading)
                    break
            if found:
                break
        if found:
            spans.append(found)
            i = found.end_tok + 1
        else:
            i += 1
    return spans


class ExpressionIndex:
    """In-memory map of written form → hiragana readings for expression/common entries."""

    def __init__(self, readings: dict[str, set[str]], key: tuple):
        self._readings = readings
        self.key = key

    def readings_for(self, form: str) -> set[str] | None:
        return self._readings.get(form)

    def __len__(self) -> int:
        return len(self._readings)


_cache: ExpressionIndex | None = None


def _index_key(db: Session) -> tuple:
    rows = db.execute(select(Dictionary.id, Dictionary.entry_count)).all()
    return tuple(sorted((r.id, r.entry_count) for r in rows))


def get_index(db: Session) -> ExpressionIndex:
    global _cache
    key = _index_key(db)
    if _cache is not None and _cache.key == key:
        return _cache
    stmt = (
        select(DictForm.entry_id, DictForm.text, DictForm.kind)
        .join(DictEntry, DictEntry.id == DictForm.entry_id)
        .where((DictEntry.is_expression == True) | (DictEntry.common == True))  # noqa: E712
    )
    by_entry: dict[int, dict[str, list[str]]] = {}
    for entry_id, text, kind in db.execute(stmt):
        by_entry.setdefault(entry_id, {"kanji": [], "kana": []})[kind].append(text)
    readings: dict[str, set[str]] = {}
    for forms in by_entry.values():
        kana = {to_hiragana(k) for k in forms["kana"]}
        for text in forms["kanji"] + forms["kana"]:
            readings.setdefault(text, set()).update(kana)
    _cache = ExpressionIndex(readings, key)
    return _cache


def reset_cache() -> None:
    global _cache
    _cache = None
