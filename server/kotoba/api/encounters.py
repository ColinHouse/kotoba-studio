"""Encounters (遇到这个词的经历)."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Encounter
from kotoba.services import learning

router = APIRouter(prefix="/encounters", tags=["encounters"])


class SenseIn(BaseModel):
    gloss_zh: str | None = None
    gloss_en: str | None = None
    origin: str = "jmdict"


class EncounterCreate(BaseModel):
    line_id: int
    headword: str = Field(min_length=1)
    reading: str = ""
    surface: str = ""
    span_start: int = 0
    span_end: int = 0
    sense: SenseIn | None = None
    pos: str | None = None
    jmdict_id: str | None = None
    card_types: list[str] = []
    owner: str | None = None


class EncounterUpdate(BaseModel):
    sense_id: int | None = None
    ai_explanation: dict | None = None
    surface: str | None = None


def get_encounter_or_404(db: Session, encounter_id: int) -> Encounter:
    enc = db.get(Encounter, encounter_id)
    if enc is None:
        raise ApiError("not_found", f"encounter {encounter_id} not found", 404)
    return enc


@router.post("", status_code=201)
def create_encounter(body: EncounterCreate, db: Session = Depends(get_db)) -> dict:
    enc = learning.add_encounter(
        db,
        line_id=body.line_id,
        headword=body.headword,
        reading=body.reading,
        surface=body.surface,
        span_start=body.span_start,
        span_end=body.span_end,
        sense=body.sense.model_dump() if body.sense else None,
        pos=body.pos,
        jmdict_id=body.jmdict_id,
    )
    cards = (
        learning.create_cards(db, enc.id, body.card_types, body.owner) if body.card_types else []
    )
    db.commit()
    detail = learning.term_detail(db, enc.term_id)
    return {
        "encounter": next(e for e in detail["encounters"] if e["id"] == enc.id),
        "term": {k: v for k, v in detail.items() if k not in ("encounters", "cards")},
        "cards": [learning.card_to_dict(c) for c in cards],
    }


@router.patch("/{encounter_id}")
def update_encounter(
    encounter_id: int, body: EncounterUpdate, db: Session = Depends(get_db)
) -> dict:
    enc = get_encounter_or_404(db, encounter_id)
    data = body.model_dump(exclude_unset=True)
    if "ai_explanation" in data:
        value = data.pop("ai_explanation")
        enc.ai_explanation_json = json.dumps(value, ensure_ascii=False) if value else None
    for key, value in data.items():
        setattr(enc, key, value)
    db.commit()
    timeline = learning.encounter_timeline(db, enc.term_id)
    return next(e for e in timeline if e["id"] == enc.id)


@router.delete("/{encounter_id}", status_code=204)
def delete_encounter(encounter_id: int, db: Session = Depends(get_db)) -> None:
    enc = get_encounter_or_404(db, encounter_id)
    db.delete(enc)
    db.commit()
