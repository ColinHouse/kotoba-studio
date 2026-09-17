"""Study statistics endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from kotoba.core.db import get_db
from kotoba.services.review import stats as stats_service

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("")
def get_stats(db: Session = Depends(get_db)) -> dict:
    """Return study statistics: volumes, retention, forecast, and source breakdown."""
    return stats_service.study_stats(db)
