"""Morphological analysis with fugashi + unidic-lite."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from functools import lru_cache

from kotoba.services.jp.kana import is_all_kana, to_hiragana

CONTENT_POS = {
    "名詞", "動詞", "形容詞", "形状詞", "副詞", "連体詞", "感動詞", "代名詞", "接頭辞", "接尾辞",
}


@dataclass(slots=True)
class Token:
    surface: str
    lemma: str
    base: str
    reading: str
    reading_base: str
    pos1: str
    pos2: str
    start: int
    end: int

    @property
    def is_content(self) -> bool:
        return self.pos1 in CONTENT_POS and self.pos2 not in {"数詞"}

    def to_dict(self) -> dict:
        d = asdict(self)
        d["is_content"] = self.is_content
        return d


@lru_cache(maxsize=1)
def _tagger():
    from fugashi import Tagger

    return Tagger()


def _feat(feature, name: str) -> str | None:
    value = getattr(feature, name, None)
    if value in (None, "*", ""):
        return None
    return value


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    cursor = 0
    for word in _tagger()(text):
        surface = word.surface
        start = text.find(surface, cursor)
        if start < 0:
            start = cursor
        end = start + len(surface)
        cursor = end
        f = word.feature
        base = _feat(f, "orthBase") or surface
        lemma = _feat(f, "lemma") or base
        kana = _feat(f, "kana")
        kana_base = _feat(f, "kanaBase")
        if kana:
            reading = to_hiragana(kana)
        elif is_all_kana(surface):
            reading = to_hiragana(surface)
        else:
            reading = surface
        reading_base = to_hiragana(kana_base) if kana_base else reading
        tokens.append(
            Token(
                surface=surface,
                lemma=lemma,
                base=base,
                reading=reading,
                reading_base=reading_base,
                pos1=_feat(f, "pos1") or "未知語",
                pos2=_feat(f, "pos2") or "",
                start=start,
                end=end,
            )
        )
    return tokens
