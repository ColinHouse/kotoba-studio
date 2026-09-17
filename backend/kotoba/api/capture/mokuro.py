"""mokuro manga OCR import: one .mokuro file or volume zip becomes an import session.

A zip is the mokuro output folder compressed — the .mokuro file plus the page
images. Its images are stored in the media directory and linked from each line,
so cards built from the reader carry the page they were picked on; a plain
.mokuro file still imports as text only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.models import CaptureSession
from kotoba.schemas import LineCreate
from kotoba.services.text.ingest import create_line
from kotoba.services.text.mokuro import load_volume

router = APIRouter(prefix="/sources", tags=["capture"])


@router.post("/{source_id}/mokuro")
async def import_mokuro(
    source_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    get_source_or_404(db, source_id)
    volume = load_volume(await file.read(), request.app.state.paths)
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
                screenshot_path=volume.image_for(block.page),
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
        "images": len(volume.images),
    }
