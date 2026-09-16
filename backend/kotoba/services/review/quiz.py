"""Session quiz (会后短测): quick checks that never touch the FSRS schedule."""

from __future__ import annotations

import random
from dataclasses import asdict, dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.errors import ApiError
from kotoba.models import Card, Encounter, Line, Term
from kotoba.services.dictionary.pitch import PATTERN_LABELS, pitches_for
from kotoba.services.jp.kana import has_kanji, kana_equal
from kotoba.services.jp.normalize import normalize_ocr

KINDS = ("reading", "cloze", "meaning", "listening", "pitch")


@dataclass(slots=True)
class QuizItem:
    card_id: int
    term_id: int
    encounter_id: int
    kind: str
    prompt: str
    answer: str
    accept: list[str]
    headword: str
    reading: str
    surface: str
    hint: str | None = None
    audio_path: str | None = None
    choices: list[str] = field(default_factory=list)

    def public(self) -> dict:
        """What the client sees before answering (answers hidden unless self-graded)."""
        d = asdict(self)
        if self.kind != "meaning":
            d["answer"] = None
            d["accept"] = []
        return d


def _first_gloss(term: Term) -> str | None:
    for sense in term.senses:
        if sense.gloss_zh:
            return sense.gloss_zh
    for sense in term.senses:
        if sense.gloss_en:
            return sense.gloss_en
    return None


def _cloze(text: str, surface: str, start: int, end: int) -> str:
    if 0 <= start < end <= len(text) and text[start:end] == surface:
        return text[:start] + "＿＿" + text[end:]
    if surface and surface in text:
        return text.replace(surface, "＿＿", 1)
    return text


def make_item(
    card: Card, enc: Encounter, line: Line, kind: str, pitches: list[dict] | None = None
) -> QuizItem | None:
    term = card.term
    if kind == "reading":
        if not term.reading or not has_kanji(term.headword):
            return None
        return QuizItem(
            card_id=card.id,
            term_id=term.id,
            encounter_id=enc.id,
            kind=kind,
            prompt=line.text,
            answer=term.reading,
            accept=[term.reading],
            headword=term.headword,
            reading=term.reading,
            surface=enc.surface,
            hint=f"写出「{term.headword}」的读音（辞书形）",
        )
    if kind == "cloze":
        return QuizItem(
            card_id=card.id,
            term_id=term.id,
            encounter_id=enc.id,
            kind=kind,
            prompt=_cloze(line.text, enc.surface, enc.span_start, enc.span_end),
            answer=enc.surface,
            accept=[enc.surface, term.headword] + ([term.reading] if term.reading else []),
            headword=term.headword,
            reading=term.reading,
            surface=enc.surface,
            hint="填入空缺处的词（原文形式）",
        )
    if kind == "meaning":
        gloss = _first_gloss(term)
        if not gloss:
            return None
        return QuizItem(
            card_id=card.id,
            term_id=term.id,
            encounter_id=enc.id,
            kind=kind,
            prompt=f"{term.headword}（{term.reading}）" if term.reading else term.headword,
            answer=gloss,
            accept=[gloss],
            headword=term.headword,
            reading=term.reading,
            surface=enc.surface,
            hint="回忆这个词在原句中的意思，然后自评",
        )
    if kind == "listening":
        if not line.audio_path:
            return None
        return QuizItem(
            card_id=card.id,
            term_id=term.id,
            encounter_id=enc.id,
            kind=kind,
            prompt="（听原声音频）",
            answer=line.text,
            accept=[line.text],
            headword=term.headword,
            reading=term.reading,
            surface=enc.surface,
            hint="听音频，写出你听到的句子",
            audio_path=line.audio_path,
        )
    if kind == "pitch":
        # Multiple recorded accents make "which pattern" ambiguous, so skip them.
        if not term.reading or not pitches:
            return None
        if len({p["accent"] for p in pitches}) != 1:
            return None
        label = pitches[0]["label"]
        return QuizItem(
            card_id=card.id,
            term_id=term.id,
            encounter_id=enc.id,
            kind=kind,
            prompt=f"{term.headword}（{term.reading}）",
            answer=label,
            accept=[label],
            headword=term.headword,
            reading=term.reading,
            surface=enc.surface,
            hint="选这个词的音高型",
            choices=list(PATTERN_LABELS.values()),
        )
    return None


def build(
    db: Session,
    session_id: int,
    kinds: tuple[str, ...] = ("reading", "cloze", "meaning"),
    limit: int = 10,
    seed: int | None = None,
) -> list[QuizItem]:
    bad = [k for k in kinds if k not in KINDS]
    if bad:
        raise ApiError("invalid_kind", f"unknown quiz kind(s): {', '.join(bad)}")
    rows = db.execute(
        select(Encounter, Line)
        .join(Line, Line.id == Encounter.line_id)
        .where(Line.session_id == session_id, Line.status != "discarded")
        .order_by(Encounter.id)
    ).all()
    items: list[QuizItem] = []
    seen_terms: set[int] = set()
    for enc, line in rows:
        if enc.term_id in seen_terms:
            continue
        cards = db.scalars(select(Card).where(Card.term_id == enc.term_id)).all()
        if not cards:
            continue
        by_type = {c.card_type: c for c in cards}
        term_pitches = pitches_for(db, enc.term.headword, enc.term.reading)
        for kind in kinds:
            card = by_type.get(kind) or cards[0]
            item = make_item(card, enc, line, kind, pitches=term_pitches)
            if item is not None:
                items.append(item)
        seen_terms.add(enc.term_id)
    rng = random.Random(seed)
    rng.shuffle(items)
    return items[:limit]


def grade(kind: str, accept: list[str], given: str | None, correct: bool | None) -> bool:
    if kind == "meaning":
        return bool(correct)
    if not given:
        return False
    given_n = normalize_ocr(given)
    if kind == "reading":
        return any(kana_equal(given_n, a) for a in accept)
    return any(given_n == normalize_ocr(a) or kana_equal(given_n, a) for a in accept)


def expected_for(db: Session, card_id: int, encounter_id: int, kind: str) -> QuizItem:
    card = db.get(Card, card_id)
    enc = db.get(Encounter, encounter_id)
    if card is None or enc is None:
        raise ApiError("not_found", "card or encounter not found", 404)
    line = db.get(Line, enc.line_id)
    item = make_item(
        card, enc, line, kind, pitches=pitches_for(db, card.term.headword, card.term.reading)
    )
    if item is None:
        raise ApiError("invalid_kind", f"kind {kind} is not available for this card")
    return item
