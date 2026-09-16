"""Subtitle import: one uploaded file becomes one import session full of lines."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.models import CaptureSession
from kotoba.schemas import LineCreate
from kotoba.services.text.encoding import decode_text
from kotoba.services.text.ingest import create_line
from kotoba.services.text.subtitles import parse_subtitles

router = APIRouter(prefix="/sources", tags=["capture"])


@router.post("/{source_id}/subtitles")
async def import_subtitles(
    source_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    cues = parse_subtitles(decode_text(await file.read()))
    session = CaptureSession(source_id=source_id, mode="import", text_source="subtitle")
    db.add(session)
    db.commit()

    created = skipped = 0
    for cue in cues:
        _, duplicate = create_line(
            db,
            LineCreate(
                session_id=session.id,
                source_id=source_id,
                text=cue.text,
                origin="subtitle",
                speaker=cue.speaker,
                start_ms=cue.start_ms,
                end_ms=cue.end_ms,
            ),
        )
        if duplicate:
            skipped += 1
        else:
            created += 1
    return {"session_id": session.id, "created": created, "skipped": skipped}
