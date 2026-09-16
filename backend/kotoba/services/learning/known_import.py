"""Import already-known words from a list, an Anki deck or a jpdb export.

Marking words known is what makes coverage and prestudy useful to someone who
already reads some Japanese. Terms that already have cards are never touched:
the user is learning those, and an import must not declare them learned.
"""

from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from collections.abc import Iterable
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, Term
from kotoba.services.jp import kana
from kotoba.services.text.encoding import decode_text

BATCH = 1000
FIELD_SEP = "\x1f"


@dataclass(slots=True)
class KnownImport:
    created: int = 0
    updated: int = 0
    skipped: int = 0
    unparsed: int = 0
    field: int | None = None

    def to_dict(self) -> dict:
        return {
            "created": self.created,
            "updated": self.updated,
            "skipped": self.skipped,
            "unparsed": self.unparsed,
            "field": self.field,
        }


def import_data(db: Session, data: bytes, fmt: str, field: int | None = None) -> KnownImport:
    """Parse `data` according to `fmt` and mark every word known."""
    if fmt == "list":
        pairs, unparsed = _parse_list(decode_text(data))
        chosen = None
    elif fmt == "jpdb":
        pairs, unparsed = _parse_jpdb(decode_text(data))
        chosen = None
    elif fmt == "anki":
        pairs, unparsed, chosen = _parse_apkg(data, field)
    else:
        raise ApiError("bad_import", f"未知的导入格式：{fmt}")
    result = _import_pairs(db, pairs)
    result.unparsed = unparsed
    result.field = chosen
    return result


def _parse_list(text: str) -> tuple[list[tuple[str, str]], int]:
    """One word per line, optional `\\t` reading, `#` comments."""
    pairs: list[tuple[str, str]] = []
    unparsed = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        headword, _, reading = line.partition("\t")
        if headword.strip():
            pairs.append((headword.strip(), reading.strip()))
        else:
            unparsed += 1
    return pairs, unparsed


def _parse_jpdb(text: str) -> tuple[list[tuple[str, str]], int]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ApiError("bad_import", "jpdb 导出不是有效的 JSON") from exc
    if isinstance(data, dict):
        data = data.get("vocabulary") or data.get("words") or data.get("items") or []
    if not isinstance(data, list):
        raise ApiError("bad_import", "无法识别的 jpdb 导出结构")
    pairs: list[tuple[str, str]] = []
    unparsed = 0
    for item in data:
        if isinstance(item, str):
            word, reading = item.strip(), ""
        elif isinstance(item, dict):
            word = str(
                item.get("spelling")
                or item.get("word")
                or item.get("headword")
                or item.get("expression")
                or ""
            ).strip()
            reading = str(item.get("reading") or "").strip()
        else:
            word, reading = "", ""
        if word:
            pairs.append((word, reading))
        else:
            unparsed += 1
    return pairs, unparsed


def _parse_apkg(data: bytes, field: int | None) -> tuple[list[tuple[str, str]], int, int]:
    """Read notes.flds from the collection inside the zip.

    Field order differs per deck, so without an explicit `field` the first
    field containing kana or kanji is used, and its index is reported back.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            name = next(
                (n for n in ("collection.anki21", "collection.anki2") if n in archive.namelist()),
                None,
            )
            if name is None:
                raise ApiError("bad_import", "不是 Anki 牌组：压缩包里没有 collection 数据库")
            raw = archive.read(name)
    except zipfile.BadZipFile as exc:
        raise ApiError("bad_import", "不是有效的 .apkg 文件") from exc

    connection = sqlite3.connect(":memory:")
    try:
        connection.deserialize(raw)
        rows = connection.execute("SELECT flds FROM notes").fetchall()
    except sqlite3.DatabaseError as exc:
        raise ApiError("bad_import", "牌组数据库无法读取") from exc
    finally:
        connection.close()

    notes = [str(row[0]).split(FIELD_SEP) for row in rows]
    chosen = field if field is not None else _japanese_field(notes)
    if chosen is None:
        raise ApiError("bad_import", "牌组里找不到含假名或汉字的字段，请用 field 指定字段序号")

    pairs: list[tuple[str, str]] = []
    unparsed = 0
    for row in notes:
        value = row[chosen].strip() if 0 <= chosen < len(row) else ""
        if value:
            pairs.append((value, ""))
        else:
            unparsed += 1
    return pairs, unparsed, chosen


def _japanese_field(notes: list[list[str]]) -> int | None:
    for row in notes:
        for index, value in enumerate(row):
            if any(kana.is_kana(c) or kana.is_kanji(c) for c in value):
                return index
    return None


def _find_term(db: Session, headword: str, reading: str) -> Term | None:
    if reading:
        term = db.scalar(select(Term).where(Term.headword == headword, Term.reading == reading))
        if term is not None:
            return term
    return db.scalar(select(Term).where(Term.headword == headword).order_by(Term.id).limit(1))


def _has_card(db: Session, term: Term) -> bool:
    return db.scalar(select(Card.id).where(Card.term_id == term.id).limit(1)) is not None


def _import_pairs(
    db: Session, pairs: Iterable[tuple[str, str]], status: str = "known"
) -> KnownImport:
    result = KnownImport()
    seen: set[tuple[str, str]] = set()
    processed = 0
    for headword, reading in pairs:
        if (headword, reading) in seen:
            continue
        seen.add((headword, reading))
        term = _find_term(db, headword, reading)
        if term is None:
            db.add(Term(headword=headword, reading=reading, known_status=status))
            result.created += 1
        elif _has_card(db, term):
            result.skipped += 1
        else:
            term.known_status = status
            result.updated += 1
        processed += 1
        if processed % BATCH == 0:
            db.commit()
    db.commit()
    return result
