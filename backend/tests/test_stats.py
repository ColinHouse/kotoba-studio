from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

from kotoba.models import CaptureSession, Card, Encounter, Line, ReviewLog, Source, Term
from kotoba.services.review.stats import study_stats


def _create_test_card(db) -> Card:
    term = Term(headword="言葉", reading="ことば")
    db.add(term)
    db.flush()
    card = Card(term_id=term.id, card_type="meaning")
    db.add(card)
    db.commit()
    return card


def test_empty_stats(client, db):
    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()

    summary = data["summary"]
    assert summary["total_cards"] == 0
    assert summary["mastered_cards"] == 0
    assert summary["total_reviews"] == 0
    assert summary["real_retention"] is None
    assert summary["target_retention"] == 0.9
    assert summary["streak_days"] == 0
    assert summary["days_active"] == 0
    assert summary["has_enough_history"] is False

    assert len(data["daily_reviews_90d"]) == 90
    assert all(d["count"] == 0 for d in data["daily_reviews_90d"])
    assert all(d["accuracy"] is None for d in data["daily_reviews_90d"])

    assert len(data["forecast_30d"]) == 30
    assert all(d["count"] == 0 for d in data["forecast_30d"])
    assert data["sources"] == []


def test_real_retention_counts_scheduled_only(client, db):
    """Invariant 1: session_quiz reviews must NEVER enter retention or review counts."""
    card = _create_test_card(db)
    now = datetime.now(UTC)

    # 3 scheduled reviews: rating 1 (fail), rating 3 (pass), rating 4 (pass) -> retention 2/3
    db.add(ReviewLog(card_id=card.id, rating=1, mode="scheduled", reviewed_at=now))
    db.add(ReviewLog(card_id=card.id, rating=3, mode="scheduled", reviewed_at=now))
    db.add(ReviewLog(card_id=card.id, rating=4, mode="scheduled", reviewed_at=now))

    # 5 session_quiz reviews: all rating 1 (should NOT pollute retention)
    for _ in range(5):
        db.add(ReviewLog(card_id=card.id, rating=1, mode="session_quiz", reviewed_at=now))
    db.commit()

    res = client.get("/api/stats")
    assert res.status_code == 200
    summary = res.json()["summary"]

    assert summary["total_reviews"] == 3
    assert round(summary["real_retention"], 4) == round(2 / 3, 4)


def test_streak_and_history_threshold(client, db):
    """Less than 14 active days must report has_enough_history=False; 14+ is True."""
    card = _create_test_card(db)
    now = datetime.now(UTC)

    # Add scheduled reviews across 5 consecutive days
    for i in range(5):
        day_time = now - timedelta(days=i)
        db.add(ReviewLog(card_id=card.id, rating=3, mode="scheduled", reviewed_at=day_time))
    db.commit()

    res = client.get("/api/stats")
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["streak_days"] == 5
    assert summary["days_active"] == 5
    assert summary["has_enough_history"] is False

    # Add 9 more distinct active days (total 14 days)
    for i in range(5, 14):
        day_time = now - timedelta(days=i)
        db.add(ReviewLog(card_id=card.id, rating=3, mode="scheduled", reviewed_at=day_time))
    db.commit()

    res = client.get("/api/stats")
    assert res.status_code == 200
    summary = res.json()["summary"]
    assert summary["days_active"] == 14
    assert summary["has_enough_history"] is True


def test_source_breakdown(client, db):
    src1 = Source(title="Steins;Gate", kind="game")
    src2 = Source(title="Clannad", kind="game")
    db.add_all([src1, src2])
    db.commit()

    session = CaptureSession(source_id=src1.id, mode="companion")
    db.add(session)
    db.commit()

    line = Line(
        source_id=src1.id,
        session_id=session.id,
        text="未来ガジェット研究所",
        text_hash="hash1",
    )
    db.add(line)
    db.commit()

    term1 = Term(headword="未来", reading="みらい")
    term2 = Term(headword="研究所", reading="けんきゅうじょ")
    db.add_all([term1, term2])
    db.commit()

    enc1 = Encounter(line_id=line.id, term_id=term1.id, surface="未来")
    enc2 = Encounter(line_id=line.id, term_id=term2.id, surface="研究所")
    db.add_all([enc1, enc2])
    db.commit()

    # Card 1: Review state (fsrs_state=2, mastered)
    # Card 2: Learning state (fsrs_state=1)
    c1 = Card(
        term_id=term1.id,
        card_type="meaning",
        primary_encounter_id=enc1.id,
        fsrs_state=2,
    )
    c2 = Card(
        term_id=term2.id,
        card_type="reading",
        primary_encounter_id=enc2.id,
        fsrs_state=1,
    )
    db.add_all([c1, c2])
    db.commit()

    res = client.get("/api/stats")
    assert res.status_code == 200
    data = res.json()
    sources = {s["title"]: s for s in data["sources"]}

    assert sources["Steins;Gate"]["cards_count"] == 2
    assert sources["Steins;Gate"]["mastered_count"] == 1
    assert sources["Clannad"]["cards_count"] == 0
    assert sources["Clannad"]["mastered_count"] == 0


def test_forecast_30d(client, db):
    now = datetime.now(UTC)
    today = now.date()
    tomorrow = datetime(today.year, today.month, today.day, tzinfo=UTC) + timedelta(days=1)

    term = Term(headword="言葉", reading="ことば")
    db.add(term)
    db.commit()

    # Card due today (overdue)
    db.add(
        Card(
            term_id=term.id,
            card_type="meaning",
            due=now - timedelta(hours=2),
            suspended=False,
        )
    )
    # Card due tomorrow
    db.add(
        Card(
            term_id=term.id,
            card_type="reading",
            due=tomorrow + timedelta(hours=3),
            suspended=False,
        )
    )
    # Card suspended (should not be counted)
    db.add(
        Card(
            term_id=term.id,
            card_type="cloze",
            due=tomorrow + timedelta(hours=3),
            suspended=True,
        )
    )
    db.commit()

    res = client.get("/api/stats")
    assert res.status_code == 200
    forecast = res.json()["forecast_30d"]

    assert forecast[0]["count"] == 1  # today (overdue)
    assert forecast[1]["count"] == 1  # tomorrow (excluding suspended)


def test_stats_query_performance_10k_reviews(db):
    """Acceptance criterion 6: aggregation must stay fast under 10k review logs."""
    card = _create_test_card(db)
    now = datetime.now(UTC)
    logs = [
        ReviewLog(
            card_id=card.id,
            rating=(i % 4) + 1,
            mode="scheduled" if i % 10 != 0 else "session_quiz",
            reviewed_at=now - timedelta(days=(i % 120), minutes=i),
        )
        for i in range(10000)
    ]
    db.bulk_save_objects(logs)
    db.commit()

    start = time.perf_counter()
    data = study_stats(db, now=now)
    elapsed_ms = (time.perf_counter() - start) * 1000

    print(f"\n[Performance Benchmark] study_stats with 10,000 logs: {elapsed_ms:.2f} ms")
    assert data["summary"]["total_reviews"] == 9000  # 10% was session_quiz
    assert elapsed_ms < 500  # well within sub-second responsiveness
