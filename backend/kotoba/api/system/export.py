"""Exports: AnkiConnect, .apkg, JSON."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba import __version__
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import (
    CaptureSession,
    Card,
    Device,
    Encounter,
    Line,
    ReviewLog,
    Sense,
    Source,
    Term,
)
from kotoba.services.export import apkg, notes
from kotoba.services.export.anki_connect import DECK_NAME, AnkiConnect

router = APIRouter(prefix="/export", tags=["export"])


class AnkiExportIn(BaseModel):
    card_ids: list[int] | None = None
    deck: str = DECK_NAME
    url: str = "http://127.0.0.1:8765"


class ApkgIn(BaseModel):
    card_ids: list[int] | None = None
    deck: str = DECK_NAME


@router.post("/anki-connect")
def anki_connect_export(
    body: AnkiExportIn, request: Request, db: Session = Depends(get_db)
) -> dict:
    export_notes = notes.notes_for_cards(db, request.app.state.paths, body.card_ids)
    if not export_notes:
        raise ApiError("nothing_to_export", "没有可导出的卡片")
    client = AnkiConnect(body.url, transport=getattr(request.app.state, "anki_transport", None))
    try:
        return client.add_notes(export_notes, body.deck)
    finally:
        client.close()


@router.post("/apkg")
def apkg_export(body: ApkgIn, request: Request, db: Session = Depends(get_db)):
    paths = request.app.state.paths
    export_notes = notes.notes_for_cards(db, paths, body.card_ids)
    if not export_notes:
        raise ApiError("nothing_to_export", "没有可导出的卡片")
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    out = paths.exports_dir / f"kotoba-{stamp}.apkg"
    apkg.build(export_notes, out, body.deck)
    return FileResponse(out, filename=out.name, media_type="application/octet-stream")


def _rows(db: Session, model) -> list[dict]:
    cols = [c.name for c in model.__table__.columns]
    out = []
    for obj in db.scalars(select(model)).all():
        row = {}
        for c in cols:
            value = getattr(obj, c)
            row[c] = value.isoformat() if isinstance(value, datetime) else value
        out.append(row)
    return out


@router.get("/json")
def json_export(db: Session = Depends(get_db)) -> dict:
    return {
        "app": "kotoba-studio",
        "version": __version__,
        "exported_at": datetime.now(UTC).isoformat(),
        "sources": _rows(db, Source),
        "sessions": _rows(db, CaptureSession),
        "lines": _rows(db, Line),
        "terms": _rows(db, Term),
        "senses": _rows(db, Sense),
        "encounters": _rows(db, Encounter),
        "cards": _rows(db, Card),
        "review_logs": _rows(db, ReviewLog),
        "devices": _rows(db, Device),
    }
