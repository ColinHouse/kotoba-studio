"""Mora counting for pitch accent.

拗音 count as one mora (きょ = 1), while 促音 and 長音 each take a mora of
their own (がっこう = 4, コーヒー = 4) and ん counts as one.
"""

from __future__ import annotations

import unicodedata

from kotoba.services.jp import kana

_SMALL = frozenset("ぁぃぅぇぉゃゅょゎァィゥェォャュョヮ")


def mora_count(reading: str) -> int:
    reading = unicodedata.normalize("NFKC", reading)
    return sum(1 for ch in reading if ch not in _SMALL and kana.is_kana(ch))
