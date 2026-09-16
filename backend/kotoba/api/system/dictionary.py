"""Dictionary endpoints."""

from __future__ import annotations

import zipfile

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.core.errors import ApiError
from kotoba.services.dictionary import jmdict, lookup, pitch, yomitan

router = APIRouter(prefix="/dict", tags=["dictionary"])


@router.get("/status")
def dict_status(db: Session = Depends(get_db)) -> dict:
    return {
        **jmdict.status(db),
        "install": jmdict.install_job.snapshot(),
        "pitch": pitch.install_job.snapshot(),
        "has_pitch": pitch.has_any(db),
    }


@router.get("/lookup")
def dict_lookup(
    q: str = Query(..., min_length=1), limit: int = 10, db: Session = Depends(get_db)
) -> dict:
    return {"query": q, "entries": [e.to_dict() for e in lookup.lookup(db, q, limit=limit)]}


@router.post("/jmdict/install", status_code=202)
def install_jmdict(request: Request, url: str | None = None) -> dict:
    started = jmdict.install_job.start(request.app.state.db.session, request.app.state.paths, url)
    return {"started": started, **jmdict.install_job.snapshot()}


@router.post("/pitch/install", status_code=202)
def install_pitch(request: Request, url: str | None = None) -> dict:
    started = pitch.install_job.start(request.app.state.db.session, request.app.state.paths, url)
    return {"started": started, **pitch.install_job.snapshot()}


@router.post("/yomitan/import")
def import_yomitan(file: UploadFile = File(...), db: Session = Depends(get_db)) -> dict:
    try:
        with zipfile.ZipFile(file.file) as archive:
            return yomitan.import_package(db, archive)
    except zipfile.BadZipFile as exc:
        raise ApiError("bad_dictionary", "上传的文件不是有效的 zip 词典包") from exc
