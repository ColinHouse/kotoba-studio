"""Sources (作品) CRUD."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import Encounter, Line, Source, Term
from kotoba.schemas import SourceCreate, SourceDTO, SourceUpdate
from kotoba.services.capture import windows
from kotoba.services.learning import coverage as coverage_service
from kotoba.services.learning import prestudy as prestudy_service

router = APIRouter(prefix="/sources", tags=["sources"])


def _counts(db: Session, source_id: int) -> tuple[int, int, int]:
    """(lines, distinct terms met here, of which already mastered)."""
    lines = db.scalar(select(func.count(Line.id)).where(Line.source_id == source_id)) or 0
    met = (
        select(func.distinct(Encounter.term_id))
        .join(Line, Line.id == Encounter.line_id)
        .where(Line.source_id == source_id)
        .subquery()
    )
    terms = db.scalar(select(func.count()).select_from(met)) or 0
    known = (
        db.scalar(
            select(func.count(Term.id)).where(
                Term.id.in_(select(met.c[0])), Term.known_status == "known"
            )
        )
        or 0
    )
    return lines, terms, known


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


@router.get("/{source_id}/coverage")
def source_coverage(source_id: int, limit: int = 50, db: Session = Depends(get_db)) -> dict:
    get_source_or_404(db, source_id)
    return coverage_service.coverage(db, source_id, limit=limit)


class PrestudyIn(BaseModel):
    limit: int = 100


@router.post("/{source_id}/prestudy")
def start_prestudy(
    source_id: int, body: PrestudyIn | None = None, db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    result = prestudy_service.build(db, source_id, (body or PrestudyIn()).limit)
    db.commit()
    return result


def _save_region(src: Source, region: dict | None) -> None:
    """Store the absolute region and keep the bound window's relative box in step.

    The UI keeps working in screen coordinates; translating to the window here
    means every later fix (moving the window, changing resolution) still lands on
    the same dialogue box without the frontend knowing about it.
    """
    absolute = windows.region_or_none(region)
    src.region_json = json.dumps(region) if absolute else None
    binding = windows.parse_binding(src.window_json)
    if binding is None or absolute is None or not windows.available():
        return
    window = windows.find_window(str(binding["process"]), binding.get("title"))
    relative = windows.relative_from_region(absolute, window) if window else None
    if relative is not None:
        binding["region"] = relative
        src.window_json = json.dumps(binding)


def _bind_window(src: Source, window: dict | None) -> None:
    """Bind (or unbind) the game window; an empty relative box becomes the default band."""
    if window is None:
        src.window_json = None
        return
    process = str(window.get("process") or "").strip()
    if not process:
        raise ApiError("invalid_value", "窗口进程名不能为空")
    title = window.get("title") or None
    relative = window.get("region")
    found = windows.find_window(process, title) if windows.available() else None
    if not isinstance(relative, dict) or not relative.get("width"):
        saved = windows.saved_region(src)
        relative = windows.relative_from_region(saved, found) if saved and found else None
        if relative is None and found is not None:
            relative = windows.default_relative_region()
    src.window_json = json.dumps({"process": process, "title": title, "region": relative})


@router.patch("/{source_id}")
def update_source(source_id: int, body: SourceUpdate, db: Session = Depends(get_db)) -> SourceDTO:
    src = get_source_or_404(db, source_id)
    data = body.model_dump(exclude_unset=True)
    if "window" in data:
        _bind_window(src, data.pop("window"))
    if "region" in data:
        _save_region(src, data.pop("region"))
    for key, value in data.items():
        setattr(src, key, value)
    db.commit()
    return SourceDTO.from_model(src, *_counts(db, src.id))


@router.delete("/{source_id}", status_code=204)
def delete_source(source_id: int, db: Session = Depends(get_db)) -> None:
    src = get_source_or_404(db, source_id)
    db.delete(src)
    db.commit()
