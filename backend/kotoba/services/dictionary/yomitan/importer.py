"""Route one Yomitan zip to the right importer: terms, frequency or pitch data."""

from __future__ import annotations

import json
import zipfile

from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.services.dictionary import pitch
from kotoba.services.dictionary.yomitan import frequency, terms
from kotoba.services.dictionary.yomitan.archive import meta_bank_names, read_index, term_bank_names


def import_package(db: Session, archive: zipfile.ZipFile) -> dict:
    """Import whatever the archive holds and describe what was imported."""
    if term_bank_names(archive):
        dictionary, entries = terms.import_archive(db, archive)
        return {
            "dictionary_id": dictionary.id,
            "title": dictionary.title,
            "kind": "terms",
            "entries": entries,
        }
    if meta_bank_names(archive):
        if _first_meta_mode(archive) == "pitch":
            index = read_index(archive)
            count = pitch.import_yomitan(db, archive)
            return {"title": index.title, "kind": "pitch", "pitches": count}
        dictionary, count = frequency.import_frequencies(db, archive)
        return {
            "dictionary_id": dictionary.id,
            "title": dictionary.title,
            "kind": "frequency",
            "frequencies": count,
        }
    raise ApiError("bad_dictionary", "词典包里没有 term_bank 或 term_meta_bank 数据")


def _first_meta_mode(archive: zipfile.ZipFile) -> str | None:
    """The first freq/pitch entry decides how a meta bank is imported."""
    for name in meta_bank_names(archive):
        with archive.open(name) as fh:
            bank = json.load(fh)
        if not isinstance(bank, list):
            continue
        for raw in bank:
            if isinstance(raw, list) and len(raw) >= 2 and raw[1] in ("freq", "pitch"):
                return str(raw[1])
    return None
