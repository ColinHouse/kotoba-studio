"""mokuro manga OCR import: one .mokuro file becomes an import session.

Only the .mokuro file is accepted (no page images), so imported lines have a
page locator but no screenshot; the reader view (#53) renders the text instead
of the page. Accepting the whole volume zip would mean storing the images in
the media directory, which is a separate decision.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.models import CaptureSession
from kotoba.schemas import LineCreate
from kotoba.services.text.encoding import decode_text
from kotoba.services.text.ingest import create_line
from kotoba.services.text.mokuro import parse_mokuro

router = APIRouter(prefix="/sources", tags=["capture"])


@router.post("/{source_id}/mokuro")
async def import_mokuro(
    source_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> dict:
    get_source_or_404(db, source_id)
    volume = parse_mokuro(decode_text(await file.read()))
    session = CaptureSession(source_id=source_id, mode="import", text_source="ocr")
    db.add(session)
    db.commit()

    created = skipped = 0
    for position, block in enumerate(volume.blocks, start=1):
        _, duplicate = create_line(
            db,
            LineCreate(
                session_id=session.id,
                source_id=source_id,
                text=block.text,
                origin="ocr",
                locator={"kind": "page", "page": block.page, "box": block.box},
                ord=position,
            ),
        )
        if duplicate:
            skipped += 1
        else:
            created += 1
    return {
        "session_id": session.id,
        "created": created,
        "skipped": skipped,
        "pages": volume.pages,
    }
