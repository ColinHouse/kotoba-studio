"""Dictionary lookups by written form."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from kotoba.models import DictEntry, DictForm, Dictionary
from kotoba.services.jp.tokenizer import Token


@dataclass(slots=True)
class EntryDTO:
    id: str
    dict_id: int
    dict_title: str
    dict_kind: str
    kanji: list[str]
    kana: list[str]
    senses: list[dict]
    pos: list[str]
    common: bool
    is_expression: bool
    usually_kana: bool = False

    @property
    def headword(self) -> str:
        """Kanji form unless the entry is usually written in kana."""
        if self.kanji and not self.usually_kana:
            return self.kanji[0]
        return self.kana[0] if self.kana else self.kanji[0]

    @property
    def reading(self) -> str:
        return self.kana[0] if self.kana else ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["headword"] = self.headword
        d["reading"] = self.reading
        return d


def entry_to_dto(entry: DictEntry, dictionary: Dictionary | None = None) -> EntryDTO:
    return EntryDTO(
        id=entry.ext_id,
        dict_id=entry.dict_id,
        dict_title=dictionary.title if dictionary else "",
        dict_kind=dictionary.kind if dictionary else "jmdict",
        kanji=[f.text for f in entry.forms if f.kind == "kanji"],
        kana=[f.text for f in entry.forms if f.kind == "kana"],
        senses=json.loads(entry.senses_json),
        pos=json.loads(entry.pos_json or "[]"),
        common=entry.common,
        is_expression=entry.is_expression,
        usually_kana=any(
            "uk" in (sense.get("misc") or []) for sense in json.loads(entry.senses_json)
        ),
    )


def lookup(db: Session, q: str, limit: int = 10) -> list[EntryDTO]:
    q = q.strip()
    if not q:
        return []
    stmt = (
        select(DictEntry, Dictionary)
        .join(DictForm, DictForm.entry_id == DictEntry.id)
        .join(Dictionary, Dictionary.id == DictEntry.dict_id)
        .where(DictForm.text == q)
        .options(selectinload(DictEntry.forms))
        .order_by(DictEntry.common.desc(), DictEntry.id)
        .limit(limit)
    )
    seen: set[int] = set()
    out: list[EntryDTO] = []
    for entry, dictionary in db.execute(stmt).unique():
        if entry.id in seen:
            continue
        seen.add(entry.id)
        out.append(entry_to_dto(entry, dictionary))
    return out


def has_form(db: Session, text: str) -> bool:
    """Whether any imported dictionary has this exact written form."""
    if not text:
        return False
    stmt = select(DictForm.id).where(DictForm.text == text).limit(1)
    return db.execute(stmt).first() is not None


def candidates_for_token(db: Session, token: Token, limit: int = 5) -> list[EntryDTO]:
    """Dictionary candidates for a token, trying surface, base form, lemma and readings."""
    keys: list[str] = []
    for key in (token.surface, token.base, token.lemma, token.reading_base, token.reading):
        if key and key not in keys:
            keys.append(key)
    out: list[EntryDTO] = []
    seen: set[tuple[int, str]] = set()
    for key in keys:
        for dto in lookup(db, key, limit=limit):
            ident = (dto.dict_id, dto.id)
            if ident in seen:
                continue
            seen.add(ident)
            out.append(dto)
            if len(out) >= limit:
                return out
    return out
