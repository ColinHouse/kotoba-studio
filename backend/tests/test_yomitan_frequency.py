import io
import json
import zipfile

from sqlalchemy import func, select

from kotoba.models import Dictionary, TermFrequency

ENTRIES = [
    ["水", "freq", 5432],
    ["猫", "freq", {"value": 100}],
    ["犬", "freq", {"frequency": 200}],
    ["鳥", "freq", {"reading": "とり", "frequency": {"value": 300, "displayValue": "300"}}],
    ["魚", "pitch", "LHH"],  # not a frequency entry
    ["虫", "freq", {"nonsense": 1}],  # no number anywhere
]


def make_zip(title: str, entries: list, *, extra_banks: tuple = ()) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "index.json",
            json.dumps({"title": title, "format": 3, "attribution": "CC BY-SA 4.0"}),
        )
        zf.writestr("term_meta_bank_1.json", json.dumps(entries))
        # A str bank is written verbatim, so a test can supply a truncated file.
        for i, bank in enumerate(extra_banks, start=2):
            zf.writestr(
                f"term_meta_bank_{i}.json",
                bank if isinstance(bank, str) else json.dumps(bank),
            )
    return buf.getvalue()


def upload(client, data: bytes):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("freq.zip", data, "application/zip")},
    )


def rank(db, headword: str, reading: str) -> int | None:
    from kotoba.services.dictionary.yomitan.frequency import rank_for

    return rank_for(db, headword, reading)


def test_import_reads_all_frequency_shapes_and_skips_the_rest(client):
    r = upload(client, make_zip("频率表", ENTRIES))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["kind"] == "frequency"
    assert body["frequencies"] == 4  # the pitch entry and the numberless entry are skipped

    entry = next(
        d for d in client.get("/api/dict/status").json()["dictionaries"] if d["title"] == "频率表"
    )
    assert entry["attribution"] == "CC BY-SA 4.0"
    assert entry["kind"] == "yomitan-freq"


def test_frequency_and_terms_with_the_same_title_coexist(client, db):
    terms_zip = io.BytesIO()
    with zipfile.ZipFile(terms_zip, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "同名", "format": 3}))
        zf.writestr(
            "term_bank_1.json",
            json.dumps([["水", "みず", "n", "", 0, ["water"], 1, []]]),
        )
    upload(client, terms_zip.getvalue())
    upload(client, make_zip("同名", [["水", "freq", 42]]))

    kinds = sorted(
        d["kind"]
        for d in client.get("/api/dict/status").json()["dictionaries"]
        if d["title"] == "同名"
    )
    assert kinds == ["yomitan", "yomitan-freq"]
    assert rank(db, "水", "") == 42
    assert (
        client.get("/api/dict/lookup", params={"q": "水"}).json()["entries"][0]["headword"] == "水"
    )


def test_rank_prefers_the_reading_and_the_smallest_rank(client, db):
    upload(client, make_zip("频率表", ENTRIES))
    assert rank(db, "水", "") == 5432
    assert rank(db, "鳥", "とり") == 300
    assert rank(db, "鳥", "ちょう") is None
    assert rank(db, "魚", "") is None

    upload(
        client,
        make_zip(
            "频率表二",
            [
                ["水", "freq", {"reading": "みず", "frequency": {"value": 999}}],
                ["犬", "freq", {"frequency": 150}],
            ],
        ),
    )
    assert rank(db, "水", "みず") == 999  # reading-specific wins over any-reading
    assert rank(db, "水", "すい") == 5432  # falls back to the any-reading row
    assert rank(db, "犬", "") == 150  # smallest rank across dictionaries


def test_same_title_replaces_the_previous_import(client, db):
    upload(client, make_zip("频率表", ENTRIES))
    upload(client, make_zip("频率表", [["水", "freq", 1]]))
    assert rank(db, "水", "") == 1
    assert rank(db, "犬", "") is None
    assert db.scalar(select(func.count(Dictionary.id)).where(Dictionary.title == "频率表")) == 1
    assert (
        db.scalar(select(func.count(TermFrequency.id)).where(TermFrequency.headword == "水")) == 1
    )


def test_term_banks_still_dispatch_to_the_term_importer(client):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("index.json", json.dumps({"title": "词表", "format": 3}))
        zf.writestr("term_bank_1.json", json.dumps([["水", "みず", "n", "", 0, ["water"], 5, []]]))
    body = upload(client, buf.getvalue()).json()
    assert body["kind"] == "terms" and body["entries"] == 1


def test_a_truncated_bank_leaves_no_half_imported_table(client):
    """Batches commit as they go, so a failure must undo what it already wrote.

    The first bank has to exceed BATCH, or the failure lands before anything is
    committed and the bug this guards against cannot reproduce.
    """
    from kotoba.services.dictionary.yomitan.frequency import BATCH

    big = [[f"語{i}", "freq", i + 1] for i in range(BATCH + 500)]
    response = upload(client, make_zip("大频率表", big, extra_banks=("{truncated",)))
    assert response.status_code >= 400
    assert response.json()["error"]["code"] == "bad_dictionary"

    db = client.app.state.db.session()
    try:
        assert (
            db.scalars(select(Dictionary).where(Dictionary.kind == "yomitan-freq")).first() is None
        )
        assert db.scalar(select(func.count(TermFrequency.id))) == 0
    finally:
        db.close()
