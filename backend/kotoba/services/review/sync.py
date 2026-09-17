"""Merge offline reviews: logs are append-only facts, card state is a replay of them.

See docs/adr/0004-offline-sync.md. Uploaded entries carry a client-generated
``client_id`` so a retry can never count the same review twice; after appending,
every touched card is recomputed from its scheduled logs in time order instead of
trusting whichever device reported last.
"""

from __future__ import annotations

from datetime import UTC
from typing import Any

from fsrs import Card as FsrsCard
from fsrs import Rating
from sqlalchemy import select
from sqlalchemy.orm import Session

from kotoba.models import Card, ReviewLog
from kotoba.services.review.scheduler import apply_fsrs_card, scheduler


def replay_card(db: Session, card: Card) -> bool:
    """Recompute the card's FSRS state from its scheduled logs, oldest first.

    Quiz logs never enter the replay (invariant 1). Returns False when there is
    nothing to replay.
    """
    logs = db.scalars(
        select(ReviewLog)
        .where(ReviewLog.card_id == card.id, ReviewLog.mode == "scheduled")
        .order_by(ReviewLog.reviewed_at, ReviewLog.id)
    ).all()
    if not logs:
        return False
    sched = scheduler(db)
    fc = FsrsCard(card_id=card.id, due=logs[0].reviewed_at)
    for log in logs:
        fc, _ = sched.review_card(fc, Rating(log.rating), review_datetime=log.reviewed_at)
    apply_fsrs_card(card, fc)
    return True


def apply_offline_reviews(db: Session, entries: list[dict[str, Any]]) -> dict:
    """Append client logs idempotently, then replay every card they touched.

    Entries whose card no longer exists are reported in ``failed`` and never
    dropped by the client. Duplicate ``client_id``s are counted as ``skipped``.
    """
    applied = skipped = 0
    failed: list[dict[str, str]] = []
    touched: set[int] = set()
    seen: set[str] = set()
    if entries:
        seen = set(
            db.scalars(
                select(ReviewLog.client_id).where(
                    ReviewLog.client_id.in_([entry["client_id"] for entry in entries])
                )
            ).all()
        )
    for entry in entries:
        client_id = str(entry["client_id"])
        if client_id in seen:
            skipped += 1
            continue
        card = db.get(Card, entry["card_id"])
        if card is None:
            failed.append({"client_id": client_id, "reason": "not_found"})
            continue
        reviewed_at = entry["reviewed_at"]
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=UTC)
        db.add(
            ReviewLog(
                card_id=card.id,
                client_id=client_id,
                rating=int(entry["rating"]),
                mode="scheduled",
                reviewed_at=reviewed_at,
                duration_ms=entry.get("duration_ms"),
                device_id=entry.get("device_id"),
                session_id=entry.get("session_id"),
            )
        )
        seen.add(client_id)  # also dedupes within one batch
        touched.add(card.id)
        applied += 1
    db.flush()
    for card_id in touched:
        card = db.get(Card, card_id)
        if card is not None:
            replay_card(db, card)
    return {"applied": applied, "skipped": skipped, "failed": failed}
