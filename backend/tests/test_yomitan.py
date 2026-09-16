import io
import json
import zipfile

INDEX = {
    "title": "测试词典",
    "revision": "2026.1",
    "format": 3,
    "author": "tester",
    "attribution": "CC BY-SA",
}

BANK = [
    ["水", "みず", "n", "", 0, ["water"], 100, []],
    ["する", "する", "vs", "", 0, ["to do"], 101, ["uk"]],
    [
        "猫",
        "ねこ",
        "n",
        "",
        0,
        [
            {"type": "text", "text": "cat"},
            {"type": "span", "content": [{"type": "text", "text": "feline"}]},
        ],
        102,
        [],
    ],
]


def make_zip(index=INDEX, banks=(BANK,)) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        if index is not None:
            zf.writestr("index.json", json.dumps(index))
        for i, bank in enumerate(banks, start=1):
            # A str bank is written verbatim, so a test can supply a truncated file.
            zf.writestr(f"term_bank_{i}.json", bank if isinstance(bank, str) else json.dumps(bank))
    return buf.getvalue()


def upload(client, data: bytes):
    return client.post(
        "/api/dict/yomitan/import",
        files={"file": ("dict.zip", data, "application/zip")},
    )


def lookup(client, q: str) -> dict:
    return client.get("/api/dict/lookup", params={"q": q}).json()["entries"][0]


def test_import_reads_index_and_term_fields(client):
    r = upload(client, make_zip())
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "测试词典"
    assert r.json()["entries"] == 3

    mizu = lookup(client, "水")
    assert mizu["id"] == "100"
    assert mizu["headword"] == "水" and mizu["reading"] == "みず"
    assert mizu["senses"][0]["gloss_en"] == ["water"]
    assert mizu["pos"] == ["n"]
    assert mizu["kanji"] == ["水"] and mizu["kana"] == ["みず"]

    suru = lookup(client, "する")
    assert suru["kana"] == ["する"] and suru["kanji"] == []
    assert suru["usually_kana"] is True  # termTags ["uk"] land in misc

    neko = lookup(client, "猫")
    assert neko["senses"][0]["gloss_en"] == ["cat", "feline"]  # structured content flattened


def test_import_replaces_the_same_title(client):
    upload(client, make_zip())
    upload(
        client,
        make_zip(banks=([["犬", "いぬ", "n", "", 0, ["dog"], 7, []]],)),
    )
    dictionaries = client.get("/api/dict/status").json()["dictionaries"]
    assert [d["title"] for d in dictionaries] == ["测试词典"]
    assert lookup(client, "犬")["id"] == "7"
    assert client.get("/api/dict/lookup", params={"q": "水"}).json()["entries"] == []


def test_entries_without_a_sequence_use_the_ordinal(client):
    bank = [["犬", "いぬ", "n", "", 0, ["dog"]], ["猫", "ねこ", "n", "", 0, ["cat"]]]
    r = upload(client, make_zip(banks=(bank,)))
    assert r.json()["entries"] == 2
    assert lookup(client, "犬")["id"] == "1"
    assert lookup(client, "猫")["id"] == "2"


def test_kana_only_expression_is_one_kana_form(client):
    bank = [["", "かな", "n", "", 0, ["kana"]]]
    upload(client, make_zip(banks=(bank,)))
    entry = lookup(client, "かな")
    assert entry["kana"] == ["かな"] and entry["kanji"] == []


def test_batching_commits_in_chunks(client, monkeypatch):
    from kotoba.services.dictionary.yomitan import terms

    monkeypatch.setattr(terms, "BATCH", 1)
    bank = [["犬", "いぬ", "n", "", 0, ["dog"], 1, []], ["猫", "ねこ", "n", "", 0, ["cat"], 2, []]]
    r = upload(client, make_zip(banks=(bank,)))
    assert r.status_code == 200 and r.json()["entries"] == 2
    assert lookup(client, "猫")["id"] == "2"


def test_bad_archives_are_rejected(client):
    r = upload(client, b"definitely not a zip")
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_dictionary"

    r = upload(client, make_zip(index=None))
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_dictionary"

    r = upload(client, make_zip(index={"revision": "2026.1"}))
    assert r.status_code == 400 and r.json()["error"]["code"] == "bad_dictionary"


def test_a_truncated_bank_leaves_no_half_imported_dictionary(client):
    """Batches commit as they go, so a failure must undo what it already wrote."""
    from sqlalchemy import func, select

    from kotoba.models import DictEntry, Dictionary

    big = [[f"語{i}", f"ご{i}", "n", "", 0, [f"gloss {i}"], i, []] for i in range(2500)]
    response = upload(client, make_zip(banks=(big, "{truncated")))
    assert response.status_code >= 400
    assert response.json()["error"]["code"] == "bad_dictionary"

    db = client.app.state.db.session()
    try:
        assert db.scalars(select(Dictionary).where(Dictionary.kind == "yomitan")).first() is None
        assert db.scalar(select(func.count(DictEntry.id))) == 0
    finally:
        db.close()
