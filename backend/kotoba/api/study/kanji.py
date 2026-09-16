"""Kanji grid, one character's terms, and a work's out-of-jōyō characters."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.models import Card, Term
from kotoba.services.learning import kanji as learning_kanji

router = APIRouter(prefix="/kanji", tags=["kanji"])


@router.get("")
def kanji_grid(scope: Literal["jouyou", "all"] = "jouyou", db: Session = Depends(get_db)) -> dict:
    data = learning_kanji.progress(db)
    if scope == "jouyou":
        data["kanji"] = [entry for entry in data["kanji"] if entry["scope"] == "jouyou"]
    data["kanji"].sort(key=learning_kanji.sort_key)
    return data


@router.get("/source/{source_id}")
def source_kanji(source_id: int, db: Session = Depends(get_db)) -> dict:
    return {"kanji": learning_kanji.out_of_jouyou(db, source_id)}


@router.get("/{character}")
def kanji_terms(character: str, db: Session = Depends(get_db)) -> dict:
    rows = db.execute(
        select(Term, func.count(Card.id))
        .outerjoin(Card, Card.term_id == Term.id)
        .where(Term.headword.contains(character))
        .group_by(Term.id)
        .order_by(Term.known_status.desc(), Term.id)
    ).all()
    return {
        "character": character,
        "terms": [
            {
                "term_id": term.id,
                "headword": term.headword,
                "reading": term.reading,
                "known_status": term.known_status,
                "has_card": bool(cards),
            }
            for term, cards in rows
        ],
    }
