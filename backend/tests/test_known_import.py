import io
import json
import sqlite3
import zipfile

FIELD_SEP = "\x1f"


def make_apkg(rows: list[list[str]]) -> bytes:
    """A minimal .apkg: a zip whose collection.anki2 holds notes.flds."""
    db = sqlite3.connect(":memory:")
    db.execute("CREATE TABLE notes (id INTEGER PRIMARY KEY, flds TEXT NOT NULL)")
    db.executemany(
        "INSERT INTO notes (flds) VALUES (?)",
        [(FIELD_SEP.join(row),) for row in rows],
    )
    db.commit()
    data = db.serialize()
    db.close()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("collection.anki2", data)
    return buf.getvalue()


def upload(client, data: bytes, fmt: str, **form):
    return client.post(
        "/api/terms/known/import",
        files={"file": ("import.bin", data, "application/octet-stream")},
        data={"format": fmt, **form},
    )


def find_term(client, headword: str) -> dict:
    terms = client.get("/api/terms", params={"q": headword}).json()
    return next(t for t in terms if t["headword"] == headword)


def seed_terms(client) -> None:
    """猫 already has a card; 犬 exists without one."""
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "猫と犬"}).json()[
        "line"
    ]
    client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "猫",
            "reading": "ねこ",
            "surface": "猫",
            "card_types": ["reading"],
        },
    )
    client.post(
        "/api/encounters",
        json={"line_id": line["id"], "headword": "犬", "reading": "いぬ", "surface": "犬"},
    )


def test_import_list_creates_updates_and_skips(client):
    seed_terms(client)
    data = "# 已知词\n猫\tねこ\n犬\tいぬ\n鳥\n\n水\tみず\n"
    r = upload(client, data.encode(), "list")
    assert r.status_code == 200, r.text
    assert r.json() == {
        "created": 2,
        "updated": 1,
        "skipped": 1,
        "unparsed": 0,
        "field": None,
    }

    assert find_term(client, "猫")["known_status"] == "learning"  # has a card: untouched
    assert find_term(client, "犬")["known_status"] == "known"
    assert find_term(client, "鳥")["reading"] == ""
    assert find_term(client, "水")["reading"] == "みず"


def test_import_accepts_shift_jis_and_rejects_unknown_encodings(client):
    assert upload(client, "猫\n".encode("cp932"), "list").json()["created"] == 1
    r = upload(client, b"\x81 ", "list")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_encoding"


def test_import_anki_picks_and_reports_the_japanese_field(client):
    apkg = make_apkg([["2043", "猫", "neko"], ["2044", "犬", "inu"]])
    body = upload(client, apkg, "anki").json()
    assert body["field"] == 1  # "2043" has no kana or kanji, "猫" does
    assert find_term(client, "猫")["known_status"] == "known"
    assert find_term(client, "犬")["known_status"] == "known"


def test_import_anki_honours_an_explicit_field(client):
    body = upload(client, make_apkg([["ねこ", "猫"]]), "anki", field=0).json()
    assert body["field"] == 0
    assert find_term(client, "ねこ")["known_status"] == "known"
    assert client.get("/api/terms", params={"q": "猫"}).json() == []


def test_import_anki_without_a_japanese_field_is_rejected(client):
    r = upload(client, make_apkg([["one", "two"]]), "anki")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_import"


def test_import_jpdb_json(client):
    data = json.dumps(
        {"vocabulary": [{"spelling": "猫", "reading": "ねこ"}, {"spelling": "犬"}]}
    ).encode()
    assert upload(client, data, "jpdb").json()["created"] == 2
    assert find_term(client, "猫")["reading"] == "ねこ"


def test_import_commits_in_batches(client, monkeypatch):
    from kotoba.services.learning import known_import

    monkeypatch.setattr(known_import, "BATCH", 1)
    r = upload(client, "鳥\n水\n犬\n".encode(), "list")
    assert r.json()["created"] == 3
    assert all(find_term(client, word)["known_status"] == "known" for word in ("鳥", "水", "犬"))


def test_unknown_format_is_rejected(client):
    r = upload(client, b"x", "csv")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_import"


def test_a_different_reading_is_a_different_word(client):
    """辛い/からい (spicy) must not mark 辛い/つらい (painful) known."""
    from sqlalchemy import select

    from kotoba.models import Term

    db = client.app.state.db.session()
    try:
        db.add(Term(headword="辛い", reading="つらい", known_status="unknown"))
        db.commit()
    finally:
        db.close()

    result = upload(client, "辛い\tからい\n".encode(), fmt="list")
    assert result.json()["created"] == 1

    db = client.app.state.db.session()
    try:
        by_reading = {
            t.reading: t.known_status
            for t in db.scalars(select(Term).where(Term.headword == "辛い")).all()
        }
        assert by_reading == {"つらい": "unknown", "からい": "known"}
    finally:
        db.close()


def test_a_reading_still_matches_a_term_whose_reading_is_unrecorded(client):
    """The narrower match must not stop an import from updating an existing row."""
    from sqlalchemy import select

    from kotoba.models import Term

    db = client.app.state.db.session()
    try:
        db.add(Term(headword="水", reading="", known_status="unknown"))
        db.commit()
    finally:
        db.close()

    result = upload(client, "水\tみず\n".encode(), fmt="list")
    assert result.json() | {"unparsed": 0} == result.json()
    assert result.json()["updated"] == 1 and result.json()["created"] == 0

    db = client.app.state.db.session()
    try:
        assert len(db.scalars(select(Term).where(Term.headword == "水")).all()) == 1
    finally:
        db.close()
