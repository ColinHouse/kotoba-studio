"""Session quiz endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Card
from kotoba.services import quiz
from kotoba.services.scheduling import fsrs_service

router = APIRouter(prefix="/quiz", tags=["quiz"])


class QuizAnswer(BaseModel):
    card_id: int
    encounter_id: int
    kind: str
    given: str | None = None
    correct: bool | None = None
    duration_ms: int | None = None
    device_id: str | None = None
    session_id: int


@router.post("/sessions/{session_id}")
def build_quiz(
    session_id: int,
    kinds: str = Query("reading,cloze,meaning"),
    limit: int = 10,
    db: Session = Depends(get_db),
) -> dict:
    kind_tuple = tuple(k.strip() for k in kinds.split(",") if k.strip())
    items = quiz.build(db, session_id, kinds=kind_tuple, limit=limit)
    return {"session_id": session_id, "items": [i.public() for i in items]}


@router.post("/answers")
def answer(body: QuizAnswer, db: Session = Depends(get_db)) -> dict:
    item = quiz.expected_for(db, body.card_id, body.encounter_id, body.kind)
    ok = quiz.grade(body.kind, item.accept, body.given, body.correct)
    card = db.get(Card, body.card_id)
    if card is None:
        raise ApiError("not_found", "card not found", 404)
    fsrs_service.review(
        db,
        card,
        3 if ok else 1,
        mode="session_quiz",
        device_id=body.device_id,
        duration_ms=body.duration_ms,
        session_id=body.session_id,
    )
    db.commit()
    return {"correct": ok, "expected": item.answer, "accept": item.accept}
