"""Sources (作品) CRUD."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Encounter, Line, Source
from kotoba.schemas import SourceCreate, SourceDTO, SourceUpdate

router = APIRouter(prefix="/sources", tags=["sources"])


def _counts(db: Session, source_id: int) -> tuple[int, int]:
    lines = db.scalar(select(func.count(Line.id)).where(Line.source_id == source_id)) or 0
    terms = (
        db.scalar(
            select(func.count(func.distinct(Encounter.term_id)))
            .join(Line, Line.id == Encounter.line_id)
            .where(Line.source_id == source_id)
        )
        or 0
    )
    return lines, terms


def get_source_or_404(db: Session, source_id: int) -> Source:
    src = db.get(Source, source_id)
    if src is None:
        raise ApiError("not_found", f"source {source_id} not found", 404)
    return src


@router.get("")
def list_sources(db: Session = Depends(get_db)) -> list[SourceDTO]:
    rows = db.scalars(select(Source).order_by(Source.created_at.desc())).all()
    return [SourceDTO.from_model(s, *_counts(db, s.id)) for s in rows]


@router.post("", status_code=201)
def create_source(body: SourceCreate, db: Session = Depends(get_db)) -> SourceDTO:
    src = Source(
        title=body.title,
        title_ja=body.title_ja,
        kind=body.kind,
        region_json=json.dumps(body.region) if body.region else None,
    )
    db.add(src)
    db.commit()
    return SourceDTO.from_model(src)


@router.get("/{source_id}")
def get_source(source_id: int, db: Session = Depends(get_db)) -> SourceDTO:
    src = get_source_or_404(db, source_id)
    return SourceDTO.from_model(src, *_counts(db, src.id))


@router.patch("/{source_id}")
def update_source(source_id: int, body: SourceUpdate, db: Session = Depends(get_db)) -> SourceDTO:
    src = get_source_or_404(db, source_id)
    data = body.model_dump(exclude_unset=True)
    if "region" in data:
        src.region_json = json.dumps(data.pop("region")) if data["region"] else None
    for key, value in data.items():
        setattr(src, key, value)
    db.commit()
    return SourceDTO.from_model(src, *_counts(db, src.id))


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> None:
    src = get_source_or_404(db, source_id)
    db.delete(src)
    db.commit()
