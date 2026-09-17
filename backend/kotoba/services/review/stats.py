"""Study statistics: review volumes, retention, due forecasts, source breakdown.

All metrics are aggregated inside SQL queries so fetching stats stays fast and
never loads thousands of ReviewLog rows into Python memory.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from kotoba.models import Card, Encounter, Line, ReviewLog, Source
from kotoba.services import settings_store


def review_streak(db: Session, today: date | None = None) -> int:
    """Consecutive days ending today (or yesterday, if today has no review yet)
    on which at least one scheduled review happened.
    """
    today = today or datetime.now(UTC).date()
    rows = db.execute(
        select(func.distinct(func.date(ReviewLog.reviewed_at))).where(ReviewLog.mode == "scheduled")
    ).all()
    days = {r[0] for r in rows if r[0]}
    if not days:
        return 0
    cursor = today if today.isoformat() in days else today - timedelta(days=1)
    streak = 0
    while cursor.isoformat() in days:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def study_stats(db: Session, now: datetime | None = None) -> dict:
    """Complete study and review metrics for the stats view."""
    now = now or datetime.now(UTC)
    today = now.date()

    # 1. Real vs target retention (scheduled reviews only)
    retention_row = db.execute(
        select(
            func.count(ReviewLog.id),
            func.sum(case((ReviewLog.rating >= 2, 1), else_=0)),
        ).where(ReviewLog.mode == "scheduled")
    ).one()
    total_reviews = int(retention_row[0] or 0)
    correct_reviews = int(retention_row[1] or 0)
    real_retention = round(correct_reviews / total_reviews, 4) if total_reviews > 0 else None
    target_retention = float(settings_store.get(db, "desired_retention") or 0.9)

    # 2. Card totals & mastery
    card_totals = db.execute(
        select(
            func.count(Card.id),
            func.sum(case((Card.fsrs_state == 2, 1), else_=0)),
        )
    ).one()
    total_cards = int(card_totals[0] or 0)
    mastered_cards = int(card_totals[1] or 0)

    # 3. Streak & active review days
    days_active = (
        db.scalar(
            select(func.count(func.distinct(func.date(ReviewLog.reviewed_at)))).where(
                ReviewLog.mode == "scheduled"
            )
        )
        or 0
    )
    streak = review_streak(db, today)
    has_enough_history = days_active >= 14

    # 4. Daily reviews and accuracy over the past 90 days
    cutoff_90d = (now - timedelta(days=89)).replace(hour=0, minute=0, second=0, microsecond=0)
    daily_rows = db.execute(
        select(
            func.date(ReviewLog.reviewed_at).label("day"),
            func.count(ReviewLog.id).label("count"),
            func.sum(case((ReviewLog.rating >= 2, 1), else_=0)).label("correct"),
        )
        .where(ReviewLog.mode == "scheduled", ReviewLog.reviewed_at >= cutoff_90d)
        .group_by(func.date(ReviewLog.reviewed_at))
    ).all()
    daily_map = {row[0]: (int(row[1]), int(row[2])) for row in daily_rows if row[0]}

    daily_reviews_90d = []
    for i in range(90):
        day_str = (today - timedelta(days=89 - i)).isoformat()
        count, correct = daily_map.get(day_str, (0, 0))
        accuracy = round(correct / count, 4) if count > 0 else None
        daily_reviews_90d.append(
            {"date": day_str, "count": count, "correct": correct, "accuracy": accuracy}
        )

    # 5. Due forecast for the next 30 days
    tomorrow_start = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)
    end_30d = tomorrow_start + timedelta(days=29)

    day0_stmt = select(func.count(Card.id)).where(
        Card.suspended.is_(False),
        (Card.due.is_(None)) | (Card.due < tomorrow_start),
    )
    day0_count = db.scalar(day0_stmt) or 0

    grouped_due_stmt = (
        select(func.date(Card.due), func.count(Card.id))
        .where(
            Card.suspended.is_(False),
            Card.due >= tomorrow_start,
            Card.due < end_30d,
        )
        .group_by(func.date(Card.due))
    )
    grouped_due = dict(db.execute(grouped_due_stmt).all())

    forecast_30d = []
    for i in range(30):
        d_str = (today + timedelta(days=i)).isoformat()
        c = int(day0_count) if i == 0 else int(grouped_due.get(d_str, 0))
        forecast_30d.append({"date": d_str, "count": c})

    # 6. Cards and mastery broken down by source
    source_rows = db.execute(
        select(
            Source.id,
            Source.title,
            func.count(func.distinct(Card.id)).label("cards_count"),
            func.count(func.distinct(case((Card.fsrs_state == 2, Card.id), else_=None))).label(
                "mastered_count"
            ),
        )
        .select_from(Source)
        .outerjoin(Line, Line.source_id == Source.id)
        .outerjoin(Encounter, Encounter.line_id == Line.id)
        .outerjoin(Card, Card.primary_encounter_id == Encounter.id)
        .group_by(Source.id, Source.title)
        .order_by(func.count(func.distinct(Card.id)).desc(), Source.id.asc())
    ).all()

    sources_summary = [
        {
            "source_id": row[0],
            "title": row[1],
            "cards_count": int(row[2] or 0),
            "mastered_count": int(row[3] or 0),
        }
        for row in source_rows
    ]

    return {
        "summary": {
            "total_cards": total_cards,
            "mastered_cards": mastered_cards,
            "total_reviews": total_reviews,
            "real_retention": real_retention,
            "target_retention": target_retention,
            "streak_days": streak,
            "days_active": days_active,
            "has_enough_history": has_enough_history,
        },
        "daily_reviews_90d": daily_reviews_90d,
        "forecast_30d": forecast_30d,
        "sources": sources_summary,
    }
