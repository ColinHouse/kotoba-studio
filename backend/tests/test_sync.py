from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from kotoba.models import Card, ReviewLog, Term
from kotoba.services.review import scheduler

BASE = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
FIELDS = ("fsrs_state", "fsrs_step", "stability", "difficulty", "due", "last_review")


def _card(db, headword: str = "世界") -> Card:
    term = Term(headword=headword, reading="せかい")
    db.add(term)
    db.flush()
    card = Card(term_id=term.id, card_type="meaning")
    db.add(card)
    db.commit()
    return card


def _entry(card_id: int, client_id: str, rating: int, when: datetime) -> dict:
    return {
        "client_id": client_id,
        "card_id": card_id,
        "rating": rating,
        "reviewed_at": when.isoformat(),
    }


def _same_state(a: Card, b: Card) -> None:
    for field in FIELDS:
        assert getattr(a, field) == getattr(b, field), field


def test_offline_reviews_replay_to_the_live_schedule(client, db):
    live = _card(db)
    offline = _card(db, headword="言葉")
    times = [BASE, BASE + timedelta(hours=20), BASE + timedelta(days=3)]
    ratings = [3, 1, 3]
    for rating, when in zip(ratings, times, strict=True):
        scheduler.review(db, live, rating, now=when)
    db.commit()

    # Uploaded out of order on purpose: the merge must sort by reviewed_at.
    res = client.post(
        "/api/reviews/sync",
        json={
            "reviews": [
                _entry(offline.id, "client-b-0001", ratings[1], times[1]),
                _entry(offline.id, "client-a-0001", ratings[0], times[0]),
                _entry(offline.id, "client-c-0001", ratings[2], times[2]),
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["applied"] == 3

    db.refresh(offline)
    db.refresh(live)
    _same_state(offline, live)


def test_reupload_is_idempotent_and_keeps_the_state(client, db):
    card = _card(db)
    reviews = [
        _entry(card.id, "client-a-0002", 3, BASE),
        _entry(card.id, "client-b-0002", 4, BASE + timedelta(days=1)),
    ]
    first = client.post("/api/reviews/sync", json={"reviews": reviews})
    assert first.json() == {"applied": 2, "skipped": 0, "failed": []}
    db.refresh(card)
    after_first = {field: getattr(card, field) for field in FIELDS}

    again = client.post("/api/reviews/sync", json={"reviews": reviews})
    assert again.json() == {"applied": 0, "skipped": 2, "failed": []}
    db.refresh(card)
    assert {field: getattr(card, field) for field in FIELDS} == after_first

    logs = db.scalar(select(func.count(ReviewLog.id)).where(ReviewLog.card_id == card.id))
    assert logs == 2


def test_unknown_card_is_reported_and_kept_on_the_client(client, db):
    card = _card(db)
    res = client.post(
        "/api/reviews/sync",
        json={
            "reviews": [
                _entry(card.id, "client-ok-0001", 3, BASE),
                _entry(999999, "client-gone-01", 3, BASE),
            ]
        },
    )
    assert res.status_code == 200
    assert res.json()["applied"] == 1
    assert res.json()["failed"] == [{"client_id": "client-gone-01", "reason": "not_found"}]


def test_live_review_id_makes_a_lost_response_retry_idempotent(client, db):
    """The online path can pre-generate the id; a retry after a lost response skips."""
    card = _card(db)
    first = client.post(
        "/api/reviews",
        json={"card_id": card.id, "rating": 3, "client_id": "client-live-01"},
    )
    assert first.status_code == 200
    db.refresh(card)
    after_first = {field: getattr(card, field) for field in FIELDS}

    retry = client.post(
        "/api/reviews/sync",
        json={"reviews": [_entry(card.id, "client-live-01", 3, BASE)]},
    )
    assert retry.json() == {"applied": 0, "skipped": 1, "failed": []}
    db.refresh(card)
    assert {field: getattr(card, field) for field in FIELDS} == after_first


def test_quiz_logs_never_enter_the_replay(client, db):
    """Invariant 1: session quizzes are logged but never schedule anything."""
    live = _card(db)
    offline = _card(db, headword="言葉")
    scheduler.review(db, live, 3, mode="session_quiz", now=BASE)
    scheduler.review(db, live, 3, now=BASE + timedelta(hours=1))
    scheduler.review(db, offline, 1, mode="session_quiz", now=BASE)
    db.commit()

    res = client.post(
        "/api/reviews/sync",
        json={"reviews": [_entry(offline.id, "client-quiz-01", 3, BASE + timedelta(hours=1))]},
    )
    assert res.status_code == 200

    db.refresh(offline)
    db.refresh(live)
    _same_state(offline, live)
    assert all(
        log.client_id for log in db.scalars(select(ReviewLog)).all()
    )  # every log now carries a stable id
