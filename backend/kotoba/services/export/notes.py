"""Build export notes (one per term) from cards, shared by AnkiConnect and .apkg export."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.core.config import Paths
from kotoba.models import Card, Encounter, Line, Source

FIELDS = [
    "Word",
    "Reading",
    "Meaning",
    "Sentence",
    "Translation",
    "Audio",
    "Image",
    "Source",
    "Explanation",
    "KotobaId",
]

CSS = """
.card { font-family: "Hiragino Sans", "Yu Gothic", "Noto Sans CJK JP", sans-serif; font-size: 18px;
  text-align: center; color: #2b2b2b; background: #faf8f3; padding: 20px; }
.box { background: #fff; border-radius: 14px; box-shadow: 0 4px 14px rgba(0,0,0,.08);
  padding: 22px; max-width: 640px; margin: 0 auto; text-align: left; }
.word { font-size: 40px; font-weight: 700; text-align: center; }
.reading { color: #7a6f5d; text-align: center; margin-bottom: 14px; }
.meaning { line-height: 1.6; }
.sentence { margin-top: 16px; padding: 12px 14px; background: #f4efe6;
  border-left: 4px solid #d9a05b; border-radius: 6px; line-height: 1.8; }
.sentence b { color: #b5541c; }
.translation { color: #6b6b6b; font-size: 15px; margin-top: 6px; }
.explanation { margin-top: 14px; font-size: 15px; background: #eef4ff; border-radius: 8px;
  padding: 10px 12px; }
.explanation dt { font-weight: 700; color: #3a5a99; margin-top: 6px; }
img { max-width: 100%; border-radius: 10px; margin-top: 14px; }
.source { color: #999; font-size: 13px; margin-top: 12px; text-align: right; }
hr { border: 0; height: 1px; background: #e6e0d4; margin: 16px 0; }
"""

FRONT = (
    '<div class="box"><div class="word">{{Word}}</div>'
    '<div style="text-align:center">{{Audio}}</div></div>'
)
BACK = """<div class="box"><div class="word">{{Word}}</div><div class="reading">{{Reading}}</div>
<div style="text-align:center">{{Audio}}</div><hr>
<div class="meaning">{{Meaning}}</div>
<div class="sentence">{{Sentence}}</div>
{{#Translation}}<div class="translation">{{Translation}}</div>{{/Translation}}
{{#Explanation}}<div class="explanation">{{Explanation}}</div>{{/Explanation}}
{{Image}}
<div class="source">{{Source}}</div></div>"""


@dataclass(slots=True)
class ExportNote:
    kotoba_id: str
    word: str
    reading: str
    meaning: str
    sentence: str
    translation: str
    source: str
    explanation: str
    image: tuple[str, Path] | None = None
    audio: tuple[str, Path] | None = None
    # Kept from before the rename so a saved `tag:kotoba-studio` search in the
    # user's Anki keeps matching newly exported notes.
    tags: list[str] = field(default_factory=lambda: ["kotoba-studio"])

    def fields(self) -> dict[str, str]:
        return {
            "Word": self.word,
            "Reading": self.reading,
            "Meaning": self.meaning,
            "Sentence": self.sentence,
            "Translation": self.translation,
            "Audio": f"[sound:{self.audio[0]}]" if self.audio else "",
            "Image": f'<img src="{self.image[0]}">' if self.image else "",
            "Source": self.source,
            "Explanation": self.explanation,
            "KotobaId": self.kotoba_id,
        }


def _highlight(text: str, surface: str, start: int, end: int) -> str:
    if 0 <= start < end <= len(text) and text[start:end] == surface:
        return f"{text[:start]}<b>{surface}</b>{text[end:]}"
    if surface and surface in text:
        return text.replace(surface, f"<b>{surface}</b>", 1)
    return text


def _explanation_html(raw: str | None) -> str:
    if not raw:
        return ""
    data = json.loads(raw)
    labels = [
        ("meaning_here", "这句里的意思"),
        ("form", "词形"),
        ("tone", "语气"),
        ("needs_context", "需要上下文"),
        ("daily_usable", "日常能否这样说"),
        ("trap_for_zh", "对中文母语者的提醒"),
    ]
    parts = [f"<dt>{label}</dt><dd>{data[key]}</dd>" for key, label in labels if data.get(key)]
    return f"<dl>{''.join(parts)}</dl>" if parts else ""


def notes_for_cards(db: Session, paths: Paths, card_ids: list[int] | None) -> list[ExportNote]:
    stmt = select(Card).order_by(Card.id)
    if card_ids:
        stmt = stmt.where(Card.id.in_(card_ids))
    notes: list[ExportNote] = []
    seen_terms: set[int] = set()
    for card in db.scalars(stmt).all():
        if card.term_id in seen_terms:
            continue
        seen_terms.add(card.term_id)
        term = card.term
        enc = db.get(Encounter, card.primary_encounter_id) if card.primary_encounter_id else None
        if enc is None:
            enc = db.scalar(
                select(Encounter).where(Encounter.term_id == term.id).order_by(Encounter.id)
            )
        line = db.get(Line, enc.line_id) if enc else None
        source = db.get(Source, line.source_id) if line and line.source_id else None
        glosses = [s.gloss_zh or s.gloss_en for s in term.senses if (s.gloss_zh or s.gloss_en)]
        sentence = _highlight(line.text, enc.surface, enc.span_start, enc.span_end) if line else ""
        image = audio = None
        if line and line.screenshot_path:
            p = paths.media_dir / line.screenshot_path
            if p.is_file():
                image = (f"kotoba_{term.id}_{p.name}", p)
        if line and line.audio_path:
            p = paths.media_dir / line.audio_path
            if p.is_file():
                audio = (f"kotoba_{term.id}_{p.name}", p)
        notes.append(
            ExportNote(
                kotoba_id=f"term:{term.id}",
                word=term.headword,
                reading=term.reading,
                meaning="<br>".join(glosses),
                sentence=sentence,
                translation=(line.translation_zh or "") if line else "",
                source=source.title if source else "Kotobako",
                explanation=_explanation_html(enc.ai_explanation_json) if enc else "",
                image=image,
                audio=audio,
            )
        )
    return notes
