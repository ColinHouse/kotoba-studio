"""Scheduled review queue and review submission."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.api.system.devices import get_device_or_404
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import Card, Device, utcnow
from kotoba.services import learning
from kotoba.services.review import scheduler

router = APIRouter(prefix="/reviews", tags=["reviews"])


class ReviewIn(BaseModel):
    card_id: int
    rating: int = Field(ge=1, le=4)
    mode: Literal["scheduled", "session_quiz"] = "scheduled"
    device_id: str | None = None
    duration_ms: int | None = None
    session_id: int | None = None


def _device_kind(db: Session, device_id: str | None, device_kind: str | None) -> str:
    if device_id:
        device = get_device_or_404(db, device_id)
        device.last_seen = utcnow()
        db.commit()
        return device.kind
    if device_kind in ("desktop", "mobile"):
        return device_kind
    raise ApiError("device_required", "pass device_id (registered) or device_kind")


def card_face(db: Session, card: Card) -> dict:
    """Everything the client needs to render a card front and back."""
    base = learning.card_to_dict(card)
    term = learning.term_summary(db, card.term)
    timeline = learning.encounter_timeline(db, card.term_id)
    encounter = next((e for e in timeline if e["id"] == card.primary_encounter_id), None)
    if encounter is None and timeline:
        encounter = timeline[-1]
    cloze_text = None
    if encounter:
        text = encounter["line_text"]
        s, e = encounter["span_start"], encounter["span_end"]
        if 0 <= s < e <= len(text) and text[s:e] == encounter["surface"]:
            cloze_text = text[:s] + "＿＿" + text[e:]
        elif encounter["surface"] and encounter["surface"] in text:
            cloze_text = text.replace(encounter["surface"], "＿＿", 1)
        else:
            cloze_text = text
    return {
        **base,
        "term": term,
        "encounter": encounter,
        "other_encounters": max(len(timeline) - (1 if encounter else 0), 0),
        "cloze_text": cloze_text,
        "preview": scheduler.preview(db, card),
    }


@router.get("/queue")
def review_queue(
    device_id: str | None = None,
    device_kind: str | None = None,
    limit: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    kind = _device_kind(db, device_id, device_kind)
    cards = scheduler.queue(db, kind, limit=limit)
    return {"device_kind": kind, "cards": [card_face(db, c) for c in cards]}


@router.post("")
def submit_review(body: ReviewIn, db: Session = Depends(get_db)) -> dict:
    card = db.get(Card, body.card_id)
    if card is None:
        raise ApiError("not_found", f"card {body.card_id} not found", 404)
    if body.device_id:
        get_device_or_404(db, body.device_id)
    scheduler.review(
        db,
        card,
        body.rating,
        mode=body.mode,
        device_id=body.device_id,
        duration_ms=body.duration_ms,
        session_id=body.session_id,
    )
    db.commit()
    return {
        "card": learning.card_to_dict(card),
        "next_due": card.due.isoformat() if card.due else None,
    }


@router.get("/forecast")
def forecast(days: int = 7, db: Session = Depends(get_db)) -> dict:
    now = datetime.now(UTC)
    out = []
    for i in range(days):
        start = (now + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        stmt = select(func.count(Card.id)).where(Card.suspended.is_(False))
        if i == 0:
            stmt = stmt.where((Card.due.is_(None)) | (Card.due < end))
        else:
            stmt = stmt.where(Card.due >= start, Card.due < end)
        out.append({"date": start.date().isoformat(), "count": db.scalar(stmt) or 0})
    devices = db.scalars(select(Device)).all()
    return {"days": out, "devices": [d.kind for d in devices]}
