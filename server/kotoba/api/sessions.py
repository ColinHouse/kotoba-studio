"""Capture sessions."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import CaptureSession, Line, utcnow
from kotoba.schemas import SessionCreate, SessionDTO
from kotoba.services import settings_store

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _line_count(db: Session, session_id: int) -> int:
    return db.scalar(select(func.count(Line.id)).where(Line.session_id == session_id)) or 0


def get_session_or_404(db: Session, session_id: int) -> CaptureSession:
    s = db.get(CaptureSession, session_id)
    if s is None:
        raise ApiError("not_found", f"session {session_id} not found", 404)
    return s


@router.get("")
def list_sessions(
    source_id: int | None = None, limit: int = 50, db: Session = Depends(get_db)
) -> list[SessionDTO]:
    stmt = select(CaptureSession).order_by(CaptureSession.started_at.desc()).limit(limit)
    if source_id is not None:
        stmt = stmt.where(CaptureSession.source_id == source_id)
    return [SessionDTO.from_model(s, _line_count(db, s.id)) for s in db.scalars(stmt).all()]


@router.post("", status_code=201)
def start_session(body: SessionCreate, db: Session = Depends(get_db)) -> SessionDTO:
    s = CaptureSession(source_id=body.source_id, mode=body.mode, text_source=body.text_source)
    db.add(s)
    db.flush()
    settings_store.set_value(db, "active_session_id", s.id)
    db.commit()
    return SessionDTO.from_model(s)


@router.get("/active")
def active_session(db: Session = Depends(get_db)) -> SessionDTO | None:
    sid = settings_store.get(db, "active_session_id")
    if sid is None:
        return None
    s = db.get(CaptureSession, sid)
    if s is None or s.ended_at is not None:
        return None
    return SessionDTO.from_model(s, _line_count(db, s.id))


@router.get("/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)) -> SessionDTO:
    s = get_session_or_404(db, session_id)
    return SessionDTO.from_model(s, _line_count(db, s.id))


@router.post("/{session_id}/end")
def end_session(session_id: int, db: Session = Depends(get_db)) -> SessionDTO:
    s = get_session_or_404(db, session_id)
    if s.ended_at is None:
        s.ended_at = utcnow()
        counts = dict(
            db.execute(
                select(Line.status, func.count(Line.id))
                .where(Line.session_id == s.id)
                .group_by(Line.status)
            ).all()
        )
        s.stats_json = json.dumps(
            {
                "lines_total": sum(counts.values()),
                "kept": counts.get("kept", 0),
                "inbox": counts.get("inbox", 0),
                "discarded": counts.get("discarded", 0),
                "duration_s": int((s.ended_at - s.started_at).total_seconds()),
            }
        )
        if settings_store.get(db, "active_session_id") == s.id:
            settings_store.set_value(db, "active_session_id", None)
        db.commit()
    return SessionDTO.from_model(s, _line_count(db, s.id))
