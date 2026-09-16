"""Yomitan dictionary archives: read the index and stream the term banks in.

Only the format is implemented; no third-party dictionary is bundled. Users
bring their own zip, which is where community 日中 dictionaries, frequency
lists and pitch data live.
"""

from kotoba.services.dictionary.yomitan.archive import (
    YomitanIndex,
    read_index,
    term_bank_names,
)
from kotoba.services.dictionary.yomitan.frequency import rank_for
from kotoba.services.dictionary.yomitan.importer import import_package
from kotoba.services.dictionary.yomitan.terms import import_archive

__all__ = [
    "YomitanIndex",
    "import_archive",
    "import_package",
    "rank_for",
    "read_index",
    "term_bank_names",
]
