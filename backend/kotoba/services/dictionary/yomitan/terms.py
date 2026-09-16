"""Stream term_bank_*.json into the dictionary tables, one bank at a time."""

from __future__ import annotations

import json
import zipfile
from typing import Any

from sqlalchemy import delete, func, insert, select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import DictEntry, DictForm, Dictionary
from kotoba.services.dictionary.yomitan.archive import YomitanIndex, read_index, term_bank_names
from kotoba.services.jp import kana

BATCH = 2000


def plain_text(node: Any) -> str:
    """A definition item as text; structured-content nodes are flattened."""
    if isinstance(node, str):
        return node
    if isinstance(node, dict):
        if isinstance(node.get("text"), str):
            return node["text"]
        if node.get("type") == "br":
            return " "
        return plain_text(node.get("content"))
    if isinstance(node, list):
        return "".join(plain_text(item) for item in node)
    return ""


def _definitions(value: Any) -> list[str] | None:
    """The gloss list, or None when the field is not a list at all."""
    if not isinstance(value, list):
        return None
    out: list[str] = []
    for item in value:
        text = plain_text(item).strip()
        if text:
            out.append(text)
    return out


def split_entry(raw: Any, ordinal: int) -> tuple[dict, list[dict]] | None:
    """One term_bank row: positional fields, per the Yomitan format."""
    if not isinstance(raw, list) or len(raw) < 6:
        return None
    expression = str(raw[0] or "").strip()
    reading = str(raw[1] or "").strip()
    definition_tags = raw[2] if isinstance(raw[2], str) else ""
    popularity = raw[4] if isinstance(raw[4], int) else 0
    glosses = _definitions(raw[5])
    if glosses is None or not (expression or reading):
        return None
    sequence = raw[6] if len(raw) > 6 and raw[6] else None
    term_tags = [str(t) for t in raw[7]] if len(raw) > 7 and isinstance(raw[7], list) else []

    written = expression or reading
    forms = [{"text": written, "kind": "kanji" if kana.has_kanji(written) else "kana"}]
    if reading and reading != written:
        forms.append({"text": reading, "kind": "kana"})
    pos = definition_tags.split()
    entry = {
        "ext_id": str(sequence or ordinal),
        "senses_json": json.dumps(
            [{"pos": pos, "gloss_en": glosses, "misc": term_tags, "field": [], "info": []}],
            ensure_ascii=False,
        ),
        "pos_json": json.dumps(pos, ensure_ascii=False),
        "common": bool(popularity),
        "is_expression": "exp" in pos,
    }
    return entry, forms


def _replace_existing(db: Session, title: str) -> None:
    for old in db.scalars(
        select(Dictionary).where(Dictionary.kind == "yomitan", Dictionary.title == title)
    ).all():
        old_entry_ids = select(DictEntry.id).where(DictEntry.dict_id == old.id)
        db.execute(delete(DictForm).where(DictForm.entry_id.in_(old_entry_ids)))
        db.execute(delete(DictEntry).where(DictEntry.dict_id == old.id))
        db.delete(old)
    db.flush()


def import_archive(db: Session, archive: zipfile.ZipFile) -> tuple[Dictionary, int]:
    """Import the archive in place of any same-titled Yomitan dictionary.

    Banks are read one file at a time and each batch of entries is committed,
    so a few hundred thousand entries never sit in memory at once.
    """
    index: YomitanIndex = read_index(archive)
    _replace_existing(db, index.title)
    dictionary = Dictionary(
        title=index.title, revision=index.revision, kind="yomitan", entry_count=0
    )
    db.add(dictionary)
    db.flush()

    next_id = (db.scalar(select(func.max(DictEntry.id))) or 0) + 1
    ordinal = 0
    imported = 0
    entry_batch: list[dict] = []
    form_batch: list[dict] = []
    try:
        for name in term_bank_names(archive):
            with archive.open(name) as fh:
                bank = json.load(fh)
            if not isinstance(bank, list):
                continue
            for raw in bank:
                ordinal += 1
                split = split_entry(raw, ordinal)
                if split is None:
                    continue
                entry, forms = split
                entry["id"] = next_id
                entry["dict_id"] = dictionary.id
                next_id += 1
                imported += 1
                for form in forms:
                    form["entry_id"] = entry["id"]
                entry_batch.append(entry)
                form_batch.extend(forms)
                if len(entry_batch) >= BATCH:
                    _commit_batch(db, entry_batch, form_batch)
                    entry_batch, form_batch = [], []
        if entry_batch:
            _commit_batch(db, entry_batch, form_batch)
    except Exception as exc:
        # Batches commit as they go, so a bank that fails half way through leaves
        # committed rows behind a dictionary that still says entry_count = 0 — an
        # "empty" dictionary whose entries nevertheless answer lookups. Undo it.
        db.rollback()
        _replace_existing(db, index.title)
        db.commit()
        if isinstance(exc, ApiError):
            raise
        raise ApiError("bad_dictionary", f"词典包读取失败：{type(exc).__name__}") from exc
    dictionary.entry_count = imported
    db.commit()
    return dictionary, imported


def _commit_batch(db: Session, entries: list[dict], forms: list[dict]) -> None:
    db.execute(insert(DictEntry), entries)
    db.execute(insert(DictForm), forms)
    db.commit()
