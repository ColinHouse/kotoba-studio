"""Import Yomitan frequency data and answer "how common is this word?"."""

from __future__ import annotations

import json
import zipfile
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from kotoba.models import Dictionary, TermFrequency
from kotoba.services.dictionary.yomitan.archive import meta_bank_names, read_index

BATCH = 2000


def parse_entry(raw: Any) -> tuple[str, str | None, int] | None:
    """`[expression, mode, data]`; only freq entries with a usable number survive."""
    if not isinstance(raw, list) or len(raw) < 3 or raw[1] != "freq":
        return None
    headword = str(raw[0] or "").strip()
    if not headword:
        return None
    parsed = _frequency(raw[2])
    if parsed is None:
        return None
    reading, rank = parsed
    return headword, reading, rank


def _frequency(data: Any) -> tuple[str | None, int] | None:
    """All three data shapes: 5432, {"value"/"frequency": n}, or with a reading."""
    if isinstance(data, bool):
        return None
    if isinstance(data, (int, float)):
        return None, int(data)
    if isinstance(data, dict):
        reading = str(data["reading"]) if data.get("reading") else None
        value = data.get("frequency", data.get("value"))
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return reading, int(value)
    return None


def rank_for(db: Session, headword: str, reading: str | None) -> int | None:
    """Rank for a word: a reading-specific row beats an any-reading one, then min."""
    base = select(func.min(TermFrequency.rank)).where(TermFrequency.headword == headword)
    if reading:
        exact = db.scalar(base.where(TermFrequency.reading == reading))
        if exact is not None:
            return int(exact)
    any_reading = db.scalar(base.where(TermFrequency.reading.is_(None)))
    return int(any_reading) if any_reading is not None else None


def import_frequencies(db: Session, archive: zipfile.ZipFile) -> tuple[Dictionary, int]:
    """Replace any same-titled Yomitan dictionary with this frequency table."""
    index = read_index(archive)
    for old in db.scalars(
        select(Dictionary).where(Dictionary.kind == "yomitan", Dictionary.title == index.title)
    ).all():
        db.execute(delete(TermFrequency).where(TermFrequency.dict_id == old.id))
        db.delete(old)
    db.flush()

    dictionary = Dictionary(
        title=index.title, revision=index.revision, kind="yomitan", entry_count=0
    )
    db.add(dictionary)
    db.flush()

    imported = 0
    batch: list[dict] = []
    for name in meta_bank_names(archive):
        with archive.open(name) as fh:
            bank = json.load(fh)
        if not isinstance(bank, list):
            continue
        for raw in bank:
            parsed = parse_entry(raw)
            if parsed is None:
                continue
            headword, reading, rank = parsed
            batch.append(
                {
                    "dict_id": dictionary.id,
                    "headword": headword,
                    "reading": reading,
                    "rank": rank,
                }
            )
            imported += 1
            if len(batch) >= BATCH:
                _commit_batch(db, batch)
                batch = []
    if batch:
        _commit_batch(db, batch)
    dictionary.entry_count = imported
    db.commit()
    return dictionary, imported


def _commit_batch(db: Session, rows: list[dict]) -> None:
    db.execute(insert(TermFrequency), rows)
    db.commit()
