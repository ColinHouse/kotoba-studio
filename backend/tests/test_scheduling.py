from datetime import UTC, datetime, timedelta

from kotoba.models import Card, ReviewLog
from kotoba.services.review import scheduler


def _card(
    client,
    text="今日は俺が奢ってやるよ。",
    headword="奢る",
    reading="おごる",
    surface="奢っ",
    types=("reading",),
    owner=None,
):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": text}).json()["line"]
    body = {
        "line_id": line["id"],
        "headword": headword,
        "reading": reading,
        "surface": surface,
        "span_start": text.index(surface),
        "span_end": text.index(surface) + len(surface),
        "card_types": list(types),
    }
    if owner:
        body["owner"] = owner
    return client.post("/api/encounters", json=body).json()["cards"]


def test_scheduled_review_advances_due(client, db):
    card_id = _card(client)[0]["id"]
    card = db.get(Card, card_id)
    now = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    assert card.due is None and card.stability is None
    scheduler.review(db, card, 3, mode="scheduled", now=now)
    db.commit()
    assert card.due is not None and card.due > now
    assert card.stability is not None and card.last_review == now
    logs = db.query(ReviewLog).filter_by(card_id=card_id).all()
    assert len(logs) == 1 and logs[0].mode == "scheduled" and logs[0].rating == 3


def test_session_quiz_never_touches_fsrs_state(client, db):
    card_id = _card(client)[0]["id"]
    card = db.get(Card, card_id)
    now = datetime(2026, 9, 16, 12, 0, tzinfo=UTC)
    scheduler.review(db, card, 3, mode="scheduled", now=now)
    db.commit()
    before = (
        card.fsrs_state,
        card.fsrs_step,
        card.stability,
        card.difficulty,
        card.due,
        card.last_review,
    )
    scheduler.review(db, card, 1, mode="session_quiz", now=now + timedelta(minutes=5))
    scheduler.review(db, card, 4, mode="session_quiz", now=now + timedelta(minutes=6))
    db.commit()
    after = (
        card.fsrs_state,
        card.fsrs_step,
        card.stability,
        card.difficulty,
        card.due,
        card.last_review,
    )
    assert before == after
    modes = [log.mode for log in db.query(ReviewLog).filter_by(card_id=card_id).all()]
    assert sorted(modes) == ["scheduled", "session_quiz", "session_quiz"]


def test_queue_respects_device_ownership(client, db):
    desk = _card(
        client, headword="猫", reading="ねこ", surface="猫", text="猫が好き。", owner="desktop"
    )[0]
    mob = _card(
        client, headword="犬", reading="いぬ", surface="犬", text="犬が好き。", owner="mobile"
    )[0]
    anyc = _card(
        client, headword="鳥", reading="とり", surface="鳥", text="鳥が好き。", owner="any"
    )[0]
    desktop_ids = {c.id for c in scheduler.queue(db, "desktop")}
    mobile_ids = {c.id for c in scheduler.queue(db, "mobile")}
    assert desktop_ids == {desk["id"], anyc["id"]}
    assert mobile_ids == {mob["id"], anyc["id"]}


def test_register_mobile_device_changes_default_owner(client):
    r = client.post("/api/devices/register", json={"name": "iPhone", "kind": "mobile"})
    assert r.status_code == 200
    dev = r.json()
    again = client.post(
        "/api/devices/register", json={"id": dev["id"], "name": "iPhone 17", "kind": "mobile"}
    ).json()
    assert again["id"] == dev["id"] and again["name"] == "iPhone 17"
    assert len(client.get("/api/devices").json()) == 1
    card = _card(client)[0]
    assert card["review_owner"] == "mobile"
    # explicit setting overrides the auto rule
    client.put("/api/settings", json={"review_owner_default": "desktop"})
    card2 = _card(client, headword="犬", reading="いぬ", surface="犬", text="犬が好き。")[0]
    assert card2["review_owner"] == "desktop"


def test_review_api_roundtrip(client):
    dev = client.post("/api/devices/register", json={"name": "Mac", "kind": "desktop"}).json()
    _card(client, types=("reading", "cloze"))
    q = client.get("/api/reviews/queue", params={"device_id": dev["id"]}).json()
    assert q["device_kind"] == "desktop" and len(q["cards"]) == 2
    face = q["cards"][0]
    assert face["term"]["headword"] == "奢る" and face["encounter"]["line_text"].startswith(
        "今日は"
    )
    assert set(face["preview"]) == {"again", "hard", "good", "easy"}
    cloze = next(c for c in q["cards"] if c["card_type"] == "cloze")
    assert cloze["cloze_text"] == "今日は俺が＿＿てやるよ。"
    r = client.post(
        "/api/reviews",
        json={"card_id": face["id"], "rating": 3, "device_id": dev["id"], "duration_ms": 4200},
    )
    assert r.status_code == 200 and r.json()["next_due"] is not None
    assert (
        client.get("/api/reviews/queue", params={"device_id": dev["id"]}).json()["cards"][0]["id"]
        != face["id"]
    )
    assert client.get("/api/reviews/queue", params={"device_id": "ghost"}).status_code == 404
    assert client.get("/api/reviews/forecast").json()["days"][0]["count"] >= 1


def test_settings_validation(client):
    assert (
        client.put("/api/settings", json={"desired_retention": 0.85}).json()["desired_retention"]
        == 0.85
    )
    assert client.get("/api/settings").json()["desired_retention"] == 0.85
    assert client.put("/api/settings", json={"desired_retention": 5}).status_code == 400
    assert (
        client.put("/api/settings", json={"nope": 1}).json()["error"]["code"] == "unknown_setting"
    )


def test_stats_reports_the_review_streak(client, db):
    from datetime import UTC, date, datetime, timedelta

    from kotoba.api.study.cards import review_streak
    from kotoba.models import ReviewLog

    card_id = _card(client)[0]["id"]
    assert client.get("/api/cards/stats").json()["streak_days"] == 0

    today = date(2026, 9, 16)
    for offset in (0, 1, 2, 5):  # a three-day run, then a gap
        db.add(
            ReviewLog(
                card_id=card_id,
                rating=3,
                mode="scheduled",
                reviewed_at=datetime(2026, 9, 16, 9, tzinfo=UTC) - timedelta(days=offset),
            )
        )
    # a quiz answer must not extend the streak
    db.add(
        ReviewLog(
            card_id=card_id,
            rating=3,
            mode="session_quiz",
            reviewed_at=datetime(2026, 9, 13, 9, tzinfo=UTC),
        )
    )
    db.commit()
    assert review_streak(db, today) == 3
    assert review_streak(db, today + timedelta(days=1)) == 3  # counts back from yesterday
    assert review_streak(db, today + timedelta(days=2)) == 0
