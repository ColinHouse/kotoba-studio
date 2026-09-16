"""中日同形词提醒。Words a Chinese reader will recognise but misread.

勉強 is not 勉强, 大丈夫 is not 大丈夫, 手紙 is not 手纸. The seed table is data,
not logic, so it can grow without touching code.
"""

from __future__ import annotations

from functools import lru_cache

from kotoba.core.resources import HOMOGRAPH_TRAPS_FILE, load_json


@lru_cache(maxsize=1)
def _traps() -> dict[str, dict]:
    return {row["headword"]: row for row in load_json(HOMOGRAPH_TRAPS_FILE)}


def homograph_trap(headword: str) -> dict | None:
    """The look-alike warning for `headword`, or None when there is nothing to flag."""
    return _traps().get(headword)
