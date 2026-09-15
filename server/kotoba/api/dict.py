"""Dictionary endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.services.dictionary import jmdict, lookup

router = APIRouter(prefix="/dict", tags=["dictionary"])


@router.get("/status")
def dict_status(db: Session = Depends(get_db)) -> dict:
    return {**jmdict.status(db), "install": jmdict.install_job.snapshot()}


@router.get("/lookup")
def dict_lookup(
    q: str = Query(..., min_length=1), limit: int = 10, db: Session = Depends(get_db)
) -> dict:
    return {"query": q, "entries": [e.to_dict() for e in lookup.lookup(db, q, limit=limit)]}


@router.post("/jmdict/install", status_code=202)
def install_jmdict(request: Request, url: str | None = None) -> dict:
    started = jmdict.install_job.start(request.app.state.db.session, request.app.state.paths, url)
    return {"started": started, **jmdict.install_job.snapshot()}
