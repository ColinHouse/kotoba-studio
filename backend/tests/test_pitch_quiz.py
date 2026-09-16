import io
import json
import zipfile

from kotoba.models import Card
from kotoba.services.dictionary import pitch


def pitch_zip(entries: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "音高表", "format": 3}))
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
    return buf.getvalue()


def import_pitches(client, entries: list):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("pitch.zip", pitch_zip(entries), "application/zip")},
    )


def seed(client, card_types=("reading",)) -> dict:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "水が好き"}).json()[
        "line"
    ]
    enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "水",
            "reading": "みず",
            "surface": "水",
            "card_types": list(card_types),
        },
    ).json()
    return {"source": src, "session": ses, "line": line, "card": enc["cards"][0]}


def test_card_face_carries_pitch_patterns(client):
    import_pitches(client, [["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}]}]])
    data = seed(client)
    queue = client.get("/api/reviews/queue", params={"device_kind": "desktop"}).json()
    face = next(c for c in queue["cards"] if c["id"] == data["card"]["id"])
    assert face["pitches"] == [
        {"reading": "みず", "accent": 0, "pattern": "heiban", "label": "平板"}
    ]


def test_card_without_pitch_data_has_no_pitches(client):
    data = seed(client)
    queue = client.get("/api/reviews/queue", params={"device_kind": "desktop"}).json()
    face = next(c for c in queue["cards"] if c["id"] == data["card"]["id"])
    assert face["pitches"] == []


def test_pitch_quiz_offers_four_choices_and_grades(client):
    import_pitches(client, [["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}]}]])
    data = seed(client)

    r = client.post(
        f"/api/quiz/sessions/{data['session']['id']}",
        params={"kinds": "pitch"},
    )
    items = r.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["kind"] == "pitch"
    assert item["answer"] is None  # the answer stays server-side before grading
    assert set(item["choices"]) == {"平板", "头高", "中高", "尾高"}

    answer = client.post(
        "/api/quiz/answers",
        json={
            "card_id": item["card_id"],
            "encounter_id": item["encounter_id"],
            "kind": "pitch",
            "given": "平板",
            "session_id": data["session"]["id"],
        },
    ).json()
    assert answer["correct"] is True and answer["expected"] == "平板"

    wrong = client.post(
        "/api/quiz/answers",
        json={
            "card_id": item["card_id"],
            "encounter_id": item["encounter_id"],
            "kind": "pitch",
            "given": "头高",
            "session_id": data["session"]["id"],
        },
    ).json()
    assert wrong["correct"] is False


def test_pitch_quiz_never_touches_the_schedule(client, db):
    import_pitches(client, [["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}]}]])
    data = seed(client)
    item = client.post(
        f"/api/quiz/sessions/{data['session']['id']}", params={"kinds": "pitch"}
    ).json()["items"][0]
    before = db.get(Card, data["card"]["id"])
    snapshot = (before.fsrs_state, before.fsrs_step, before.due, before.stability)

    client.post(
        "/api/quiz/answers",
        json={
            "card_id": item["card_id"],
            "encounter_id": item["encounter_id"],
            "kind": "pitch",
            "given": "平板",
            "session_id": data["session"]["id"],
        },
    )
    db.expire_all()
    after = db.get(Card, data["card"]["id"])
    assert (after.fsrs_state, after.fsrs_step, after.due, after.stability) == snapshot


def test_no_pitch_data_means_no_pitch_questions(client):
    data = seed(client)
    r = client.post(f"/api/quiz/sessions/{data['session']['id']}", params={"kinds": "pitch"})
    assert r.json()["items"] == []


def test_ambiguous_multi_pitch_words_are_skipped(client):
    import_pitches(
        client,
        [["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}, {"position": 2}]}]],
    )
    data = seed(client)
    r = client.post(f"/api/quiz/sessions/{data['session']['id']}", params={"kinds": "pitch"})
    assert r.json()["items"] == []


def test_pitch_lookup_prefers_the_term_reading(client, db):
    import_pitches(
        client,
        [
            ["水", "pitch", {"reading": "みず", "pitches": [{"position": 0}]}],
            ["水", "pitch", {"reading": "すい", "pitches": [{"position": 1}]}],
        ],
    )
    assert [p["accent"] for p in pitch.pitches_for(db, "水", "みず")] == [0]
    assert [p["accent"] for p in pitch.pitches_for(db, "水", "すい")] == [1]
    assert len(pitch.pitches_for(db, "水", "")) == 2  # no reading: every recorded pitch
