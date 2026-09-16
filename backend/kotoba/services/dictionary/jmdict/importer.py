"""Load jmdict-simplified JSON into the dictionary tables."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from kotoba.models import DictEntry, DictForm, Dictionary

BATCH = 2000


def _entry_rows(word: dict, entry_id: int, dict_id: int) -> tuple[dict, list[dict]]:
    senses = []
    pos_all: list[str] = []
    for s in word.get("sense", []):
        pos = s.get("partOfSpeech", [])
        pos_all.extend(p for p in pos if p not in pos_all)
        senses.append(
            {
                "pos": pos,
                "gloss_en": [
                    g["text"] for g in s.get("gloss", []) if g.get("lang", "eng") == "eng"
                ],
                "misc": s.get("misc", []),
                "field": s.get("field", []),
                "info": s.get("info", []),
            }
        )
    forms = []
    common = False
    for k in word.get("kanji", []):
        forms.append(
            {
                "entry_id": entry_id,
                "text": k["text"],
                "kind": "kanji",
                "common": bool(k.get("common")),
            }
        )
        common = common or bool(k.get("common"))
    for k in word.get("kana", []):
        forms.append(
            {
                "entry_id": entry_id,
                "text": k["text"],
                "kind": "kana",
                "common": bool(k.get("common")),
            }
        )
        common = common or bool(k.get("common"))
    entry = {
        "id": entry_id,
        "dict_id": dict_id,
        "ext_id": str(word["id"]),
        "senses_json": json.dumps(senses, ensure_ascii=False),
        "pos_json": json.dumps(pos_all, ensure_ascii=False),
        "common": common,
        "is_expression": "exp" in pos_all,
    }
    return entry, forms


def import_json(
    db: Session,
    path: Path,
    title: str = "JMdict (eng)",
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Replace any existing JMdict dictionary with the contents of `path`. Returns entry count."""
    with path.open(encoding="utf-8") as fh:
        data = json.load(fh)
    words = data["words"]

    for old in db.scalars(select(Dictionary).where(Dictionary.kind == "jmdict")).all():
        old_entry_ids = select(DictEntry.id).where(DictEntry.dict_id == old.id)
        db.execute(delete(DictForm).where(DictForm.entry_id.in_(old_entry_ids)))
        db.execute(delete(DictEntry).where(DictEntry.dict_id == old.id))
        db.delete(old)
    db.flush()

    dictionary = Dictionary(
        title=title,
        revision=str(data.get("dictDate") or data.get("version") or ""),
        kind="jmdict",
        entry_count=len(words),
    )
    db.add(dictionary)
    db.flush()

    next_id = (db.scalar(select(func.max(DictEntry.id))) or 0) + 1
    entry_batch: list[dict] = []
    form_batch: list[dict] = []
    total = len(words)
    for i, word in enumerate(words):
        entry, forms = _entry_rows(word, next_id + i, dictionary.id)
        entry_batch.append(entry)
        form_batch.extend(forms)
        if len(entry_batch) >= BATCH:
            db.execute(insert(DictEntry), entry_batch)
            db.execute(insert(DictForm), form_batch)
            entry_batch, form_batch = [], []
            if progress:
                progress(i + 1, total)
    if entry_batch:
        db.execute(insert(DictEntry), entry_batch)
        db.execute(insert(DictForm), form_batch)
    db.commit()
    if progress:
        progress(total, total)
    return total


def status(db: Session) -> dict:
    dicts = db.scalars(select(Dictionary).order_by(Dictionary.id)).all()
    return {
        "installed": any(d.kind == "jmdict" for d in dicts),
        "dictionaries": [
            {
                "id": d.id,
                "title": d.title,
                "kind": d.kind,
                "revision": d.revision,
                "entry_count": d.entry_count,
                "imported_at": d.imported_at.isoformat(),
            }
            for d in dicts
        ],
    }
