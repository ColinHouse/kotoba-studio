"""Route one Yomitan zip to the right importer: terms or frequency data."""

from __future__ import annotations

import zipfile

from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.services.dictionary.yomitan import frequency, terms
from kotoba.services.dictionary.yomitan.archive import meta_bank_names, term_bank_names


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
        dictionary, count = frequency.import_frequencies(db, archive)
        return {
            "dictionary_id": dictionary.id,
            "title": dictionary.title,
            "kind": "frequency",
            "frequencies": count,
        }
    raise ApiError("bad_dictionary", "词典包里没有 term_bank 或 term_meta_bank 数据")
