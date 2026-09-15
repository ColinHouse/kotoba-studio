"""Terms (词条) and bulk known-status updates."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from kotoba.db import get_db
from kotoba.errors import ApiError
from kotoba.models import Term
from kotoba.services import learning

router = APIRouter(prefix="/terms", tags=["terms"])

KnownStatus = Literal["unknown", "learning", "known", "ignored"]


class TermUpdate(BaseModel):
    known_status: KnownStatus | None = None
    note: str | None = None
    reading: str | None = None


class BulkKnown(BaseModel):
    headwords: list[str]
    status: KnownStatus = "known"


@router.get("")
def list_terms(
    q: str | None = None,
    status: KnownStatus | None = None,
    source_id: int | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
) -> list[dict]:
    return learning.search_terms(db, q, status, source_id, limit, offset)


@router.post("/bulk-known")
def bulk_known(body: BulkKnown, db: Session = Depends(get_db)) -> dict:
    count = learning.bulk_set_status(db, body.headwords, body.status)
    db.commit()
    return {"updated": count}


@router.get("/{term_id}")
def get_term(term_id: int, db: Session = Depends(get_db)) -> dict:
    return learning.term_detail(db, term_id)


@router.patch("/{term_id}")
def update_term(term_id: int, body: TermUpdate, db: Session = Depends(get_db)) -> dict:
    term = db.get(Term, term_id)
    if term is None:
        raise ApiError("not_found", f"term {term_id} not found", 404)
    for key, value in body.model_dump(exclude_unset=True).items():
        setattr(term, key, value)
    db.commit()
    return learning.term_detail(db, term_id)
