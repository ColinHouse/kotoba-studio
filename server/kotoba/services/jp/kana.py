"""Kana / kanji helpers."""

from __future__ import annotations

import unicodedata

_HIRA = (0x3041, 0x3096)
_KATA = (0x30A1, 0x30F6)
_SHIFT = 0x60


def to_hiragana(s: str) -> str:
    return "".join(
        chr(ord(c) - _SHIFT) if _KATA[0] <= ord(c) <= _KATA[1] else c for c in s
    )


def to_katakana(s: str) -> str:
    return "".join(
        chr(ord(c) + _SHIFT) if _HIRA[0] <= ord(c) <= _HIRA[1] else c for c in s
    )


def is_kanji(ch: str) -> bool:
    cp = ord(ch)
    return (
        0x4E00 <= cp <= 0x9FFF
        or 0x3400 <= cp <= 0x4DBF
        or 0xF900 <= cp <= 0xFAFF
        or 0x20000 <= cp <= 0x2FA1F
        or ch in "々〆"
    )


def is_kana(ch: str) -> bool:
    cp = ord(ch)
    return 0x3041 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF


def has_kanji(s: str) -> bool:
    return any(is_kanji(c) for c in s)


def is_all_kana(s: str) -> bool:
    return bool(s) and all(is_kana(c) or c == "ー" for c in s)


def kana_equal(a: str, b: str) -> bool:
    """Compare two readings ignoring script (hiragana vs katakana), width and whitespace."""

    def norm(s: str) -> str:
        s = unicodedata.normalize("NFKC", s)
        s = "".join(s.split())
        return to_hiragana(s)

    return norm(a) == norm(b)
