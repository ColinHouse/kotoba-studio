import io
import json
import zipfile

from sqlalchemy import select

from kotoba.models import Card, Term
from kotoba.services.learning import prestudy


def frequency_zip(entries: list) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "频率表", "format": 3}))
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
    return buf.getvalue()


def seed_work(client) -> tuple[int, dict[str, int]]:
    """A work whose unknown words are 猫 (rank 10), 犬 (rank 50) and 鳥 (no rank)."""
    client.post(
        "/api/dict/yomitan/import",
        files={
            "file": (
                "freq.zip",
                frequency_zip([["猫", "freq", 10], ["犬", "freq", 50]]),
                "application/zip",
            )
        },
    )
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "猫と犬と鳥"}).json()[
        "line"
    ]
    terms: dict[str, int] = {}
    for headword in ("猫", "犬", "鳥"):
        enc = client.post(
            "/api/encounters",
            json={
                "line_id": line["id"],
                "headword": headword,
                "reading": "",
                "surface": headword,
            },
        )
        terms[headword] = enc.json()["term"]["id"]
    return src["id"], terms


def cards_of(db, term_id: int) -> list[Card]:
    return list(db.scalars(select(Card).where(Card.term_id == term_id)).all())


def test_prestudy_creates_cards_for_the_top_unknown_words(client, db):
    source_id, terms = seed_work(client)
    body = client.post(f"/api/sources/{source_id}/prestudy", json={"limit": 2}).json()
    assert body == {"created": 2, "skipped": 0}

    for headword in ("猫", "犬"):  # rank 10 first, then 50
        assert {card.card_type for card in cards_of(db, terms[headword])} == {
            "reading",
            "cloze",
        }
        assert db.get(Term, terms[headword]).known_status == "learning"
    assert cards_of(db, terms["鳥"]) == []  # over the limit

    # Running it again skips the words that already have cards.
    again = client.post(f"/api/sources/{source_id}/prestudy", json={"limit": 2}).json()
    assert again == {"created": 0, "skipped": 2}


def test_prestudy_skips_words_that_already_have_cards(client, db):
    source_id, terms = seed_work(client)
    line_id = client.get("/api/lines", params={"source_id": source_id}).json()[0]["id"]
    client.post(
        "/api/encounters",
        json={
            "line_id": line_id,
            "headword": "犬",
            "reading": "",
            "surface": "犬",
            "card_types": ["reading"],
        },
    )
    body = client.post(f"/api/sources/{source_id}/prestudy", json={"limit": 2}).json()
    assert body["skipped"] == 1 and body["created"] == 1
    assert {card.card_type for card in cards_of(db, terms["犬"])} == {"reading"}


def test_prestudy_rejects_an_oversized_limit(client):
    source_id, _ = seed_work(client)
    r = client.post(f"/api/sources/{source_id}/prestudy", json={"limit": 501})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "too_many"


def test_prestudy_card_without_an_encounter_renders(client, db):
    """Prestudy happens before playing, so a word may have no context at all."""
    term = Term(headword="謎", reading="なぞ")
    db.add(term)
    db.commit()

    cards = prestudy.cards_for_term(db, term, encounter_id=None, owner="desktop")
    db.commit()
    assert len(cards) == 2
    assert all(card.primary_encounter_id is None for card in cards)

    queue = client.get("/api/reviews/queue", params={"device_kind": "desktop"}).json()
    face = next(c for c in queue["cards"] if c["term"]["id"] == term.id)
    assert face["term"]["headword"] == "謎"
    assert face["encounter"] is None and face["cloze_text"] is None


def test_unknown_source(client):
    r = client.post("/api/sources/999/prestudy", json={"limit": 10})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
