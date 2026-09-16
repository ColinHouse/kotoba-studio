"""Subtitle import: one uploaded file becomes one import session full of lines."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession
from kotoba.schemas import LineCreate
from kotoba.services.text.ingest import create_line
from kotoba.services.text.subtitles import parse_subtitles

router = APIRouter(prefix="/sources", tags=["capture"])

_ENCODINGS = ("utf-8", "utf-8-sig", "cp932")


def _decode(data: bytes) -> str:
    for encoding in _ENCODINGS:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ApiError("bad_encoding", "字幕文件编码无法识别（支持 UTF-8 与 Shift_JIS）")


@router.post("/{source_id}/subtitles")
async def import_subtitles(
    source_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    cues = parse_subtitles(_decode(await file.read()))
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
