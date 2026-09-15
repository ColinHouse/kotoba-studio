"""Captured lines (台词) and their analysis."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Encounter, Line
from kotoba.schemas import LineCreate, LineCreated, LineDTO, LineUpdate
from kotoba.services import analysis
from kotoba.services.jp.normalize import normalize_ocr, text_hash
from kotoba.services.lines_service import create_line

router = APIRouter(prefix="/lines", tags=["lines"])


def get_line_or_404(db: Session, line_id: int) -> Line:
    line = db.get(Line, line_id)
    if line is None:
        raise ApiError("not_found", f"line {line_id} not found", 404)
    return line


def _encounter_count(db: Session, line_id: int) -> int:
    return db.scalar(select(func.count(Encounter.id)).where(Encounter.line_id == line_id)) or 0


@router.get("")
def list_lines(
    session_id: int | None = None,
    source_id: int | None = None,
    status: str | None = None,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[LineDTO]:
    stmt = (
        select(Line).order_by(Line.captured_at.desc(), Line.id.desc()).limit(limit).offset(offset)
    )
    if session_id is not None:
        stmt = stmt.where(Line.session_id == session_id)
    if source_id is not None:
        stmt = stmt.where(Line.source_id == source_id)
    if status is not None:
        stmt = stmt.where(Line.status == status)
    return [
        LineDTO.from_model(line, _encounter_count(db, line.id)) for line in db.scalars(stmt).all()
    ]


@router.post("", response_model=LineCreated)
def post_line(body: LineCreate, response: Response, db: Session = Depends(get_db)) -> LineCreated:
    line, duplicate = create_line(db, body)
    response.status_code = 200 if duplicate else 201
    return LineCreated(
        line=LineDTO.from_model(line, _encounter_count(db, line.id)), duplicate=duplicate
    )


@router.get("/{line_id}")
def get_line(line_id: int, db: Session = Depends(get_db)) -> LineDTO:
    line = get_line_or_404(db, line_id)
    return LineDTO.from_model(line, _encounter_count(db, line.id))


@router.patch("/{line_id}")
def update_line(line_id: int, body: LineUpdate, db: Session = Depends(get_db)) -> LineDTO:
    line = get_line_or_404(db, line_id)
    data = body.model_dump(exclude_unset=True)
    if "text" in data:
        line.text = normalize_ocr(data.pop("text"))
        line.text_hash = text_hash(line.text)
        line.tokens_json = None
    for key, value in data.items():
        setattr(line, key, value)
    db.commit()
    return LineDTO.from_model(line, _encounter_count(db, line.id))


@router.delete("/{line_id}", status_code=204)
def delete_line(line_id: int, db: Session = Depends(get_db)) -> None:
    line = get_line_or_404(db, line_id)
    db.delete(line)
    db.commit()


@router.post("/{line_id}/analyze")
def analyze(line_id: int, force: bool = False, db: Session = Depends(get_db)) -> dict:
    line = get_line_or_404(db, line_id)
    return analysis.analyze_line(db, line, force=force)
