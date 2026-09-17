"""Reader endpoints: a work's pages, ready to flip through.

The payload is one page at a time on the wire, but the reader holds the whole
volume in memory — it is text and locators, small even for 300 pages, while the
page images are requested lazily from `/media` as pages are reached.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kotoba.api.capture.sources import get_source_or_404
from kotoba.core.db import get_db
from kotoba.services.text import pages as pages_service

router = APIRouter(prefix="/sources", tags=["reader"])


@router.get("/{source_id}/pages")
def source_pages(source_id: int, db: Session = Depends(get_db)) -> dict:
    source = get_source_or_404(db, source_id)
    return {
        "source_id": source.id,
        "title": source.title,
        "title_ja": source.title_ja,
        "pages": [
            {
                "page": group.page,
                "image": group.image,
                "blocks": [asdict(block) for block in group.blocks],
            }
            for group in pages_service.source_pages(db, source_id)
        ],
    }
