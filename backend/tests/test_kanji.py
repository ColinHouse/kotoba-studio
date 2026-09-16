import json
import time

import pytest

from kotoba.models import Card, Encounter, Kanji, Line, Source, Term
from kotoba.services.dictionary import kanjidic

KANJIDIC = """<?xml version="1.0" encoding="UTF-8"?>
<kanjidic2>
  <header>
    <file_version>1.6</file_version>
    <database_version>2026-01</database_version>
    <date_of_creation>2026-01-01</date_of_creation>
  </header>
  <character>
    <literal>山</literal>
    <misc><grade>1</grade><stroke_count>3</stroke_count><freq>131</freq><jlpt>4</jlpt></misc>
    <reading_meaning>
      <rmgroup>
        <reading r_type="ja_on">サン</reading>
        <reading r_type="ja_on">セン</reading>
        <reading r_type="ja_kun">やま</reading>
        <reading r_type="korean_h">산</reading>
      </rmgroup>
    </reading_meaning>
  </character>
  <character>
    <literal>川</literal>
    <misc><grade>1</grade><stroke_count>3</stroke_count></misc>
    <reading_meaning><rmgroup><reading r_type="ja_on">セン</reading></rmgroup></reading_meaning>
  </character>
  <character>
    <literal>煌</literal>
    <misc><grade>9</grade><stroke_count>13</stroke_count></misc>
    <reading_meaning><rmgroup><reading r_type="ja_on">コウ</reading></rmgroup></reading_meaning>
  </character>
</kanjidic2>
"""


def import_fixture(db) -> int:
    return kanjidic.import_bytes(db, KANJIDIC.encode())


def add_term(db, headword: str, reading: str = "", known: bool = False, card: bool = False) -> Term:
    term = Term(headword=headword, reading=reading, known_status="known" if known else "unknown")
    db.add(term)
    db.flush()
    if card:
        db.add(Card(term_id=term.id, card_type="recognition"))
    return term


def wait_for(predicate, timeout: float = 5.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.02)
    return predicate()


def test_import_reads_the_kanjidic2_fields(db):
    assert import_fixture(db) == 3
    yama = db.get(Kanji, "山")
    assert (yama.grade, yama.stroke_count, yama.jlpt, yama.frequency) == (1, 3, 4, 131)
    assert json.loads(yama.on_readings_json) == ["サン", "セン"]
    assert json.loads(yama.kun_readings_json) == ["やま"]
    assert "korean_h" not in yama.on_readings_json


def test_reimport_replaces_the_previous_table(db):
    import_fixture(db)
    kanjidic.import_bytes(db, KANJIDIC.replace("煌", "燦").replace("grade>9", "grade>8").encode())
    assert db.get(Kanji, "煌") is None
    assert db.get(Kanji, "燦") is not None


def test_parse_rejects_a_file_without_characters():
    with pytest.raises(ValueError):
        kanjidic.parse_kxml(b"<kanjidic2><header/></kanjidic2>")


def test_grid_buckets_by_what_the_learner_knows(client, db):
    import_fixture(db)
    add_term(db, "山田", "やまだ")
    add_term(db, "山", "やま", known=True)
    add_term(db, "川柳", "せんりゅう")
    add_term(db, "煌めき", "きらめき", card=True)
    db.commit()

    grid = client.get("/api/kanji").json()
    assert grid["installed"] is True
    assert [entry["character"] for entry in grid["kanji"]] == ["山", "川"]
    yama, kawa = grid["kanji"]
    assert yama["terms"] == 2  # 山田 + 山, one of them known
    assert yama["status"] == "learning"
    assert kawa["terms"] == 1 and kawa["status"] == "seen"
    assert grid["summary"]["total"] == 2
    assert grid["summary"]["unseen"] == 0

    all_kanji = client.get("/api/kanji", params={"scope": "all"}).json()["kanji"]
    assert all_kanji[-1]["character"] == "煌"


def test_mastered_needs_every_term_known(client, db):
    import_fixture(db)
    add_term(db, "山", "やま", known=True)
    db.commit()
    entry = client.get("/api/kanji").json()["kanji"][0]
    assert entry["status"] == "mastered"


def test_kanji_terms_lists_the_terms_containing_the_character(client, db):
    import_fixture(db)
    add_term(db, "山田", "やまだ")
    add_term(db, "山", "やま", known=True, card=True)
    db.commit()

    payload = client.get("/api/kanji/山").json()
    assert payload["character"] == "山"
    assert {term["headword"] for term in payload["terms"]} == {"山田", "山"}
    yama = next(term for term in payload["terms"] if term["headword"] == "山")
    assert yama["has_card"] is True and yama["known_status"] == "known"
    assert client.get("/api/kanji/無").json()["terms"] == []


def test_source_lists_the_characters_outside_the_jouyou_table(client, db):
    import_fixture(db)
    source = Source(title="作品")
    term = Term(headword="煌めき", reading="きらめき")
    line = Line(text="煌めきが消えた。", text_hash="hash", source=source)
    db.add_all([source, term, line])
    db.flush()
    db.add(Encounter(line_id=line.id, term_id=term.id, surface="煌めき"))
    db.commit()

    payload = client.get(f"/api/kanji/source/{source.id}").json()
    assert [item["character"] for item in payload["kanji"]] == ["煌"]
    assert payload["kanji"][0]["occurrences"] == 1
    assert payload["kanji"][0]["grade"] == 9


def test_install_job_imports_and_reports_status(client, monkeypatch):
    monkeypatch.setattr(kanjidic, "download", lambda dest_dir, url: KANJIDIC.encode())
    started = client.post("/api/dict/kanjidic/install").json()
    assert started["started"] is True
    assert wait_for(lambda: client.get("/api/dict/status").json()["kanjidic"]["state"] == "done"), (
        client.get("/api/dict/status").json()
    )

    db = client.app.state.db.session()
    try:
        assert db.get(Kanji, "山") is not None
    finally:
        db.close()
    assert client.get("/api/dict/status").json()["kanjidic_installed"] is True
