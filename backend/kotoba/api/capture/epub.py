"""EPUB import: one uploaded light novel becomes an import session of sentences.

The upload is read twice: once to validate every spine document, once to import.
That way a malformed chapter fails before any line is written, and the import
still streams chapter by chapter with one commit per batch of lines.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.models import CaptureSession
from kotoba.schemas import LineCreate
from kotoba.services.text.epub import iter_chapters, validate_epub
from kotoba.services.text.ingest import create_lines

router = APIRouter(prefix="/sources", tags=["capture"])

BATCH_SIZE = 500


@router.post("/{source_id}/epub")
async def import_epub(
    source_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    validate_epub(file.file)
    file.file.seek(0)

    session = CaptureSession(source_id=source_id, mode="import", text_source="subtitle")
    db.add(session)
    db.commit()
    session_id = session.id

    created = skipped = chapters = position = 0
    batch: list[LineCreate] = []
    for chapter in iter_chapters(file.file):
        chapters += 1
        for sentence in chapter.sentences:
            position += 1
            batch.append(
                LineCreate(
                    session_id=session_id,
                    source_id=source_id,
                    text=sentence.text,
                    raw_text=sentence.raw_text,
                    origin="subtitle",
                    locator={
                        "kind": "offset",
                        "chapter": chapter.number,
                        "start": sentence.start,
                        "end": sentence.end,
                    },
                    ord=position,
                )
            )
            if len(batch) >= BATCH_SIZE:
                batch_created, batch_skipped = create_lines(db, batch)
                created += batch_created
                skipped += batch_skipped
                batch.clear()
                db.expunge_all()
    if batch:
        batch_created, batch_skipped = create_lines(db, batch)
        created += batch_created
        skipped += batch_skipped
        batch.clear()
        db.expunge_all()

    if chapters == 0:
        db.delete(session)
        db.commit()
        raise ApiError("bad_epub", "没有可导入的文本")

    return {"session_id": session_id, "created": created, "skipped": skipped, "chapters": chapters}
