from kotoba.core.resources import JMDICT_FIXTURE_FILE
from kotoba.services.dictionary import jmdict, lookup
from kotoba.services.jp import expressions
from kotoba.services.jp.tokenizer import tokenize


def test_import_and_lookup(db, jmdict_fixture):
    assert jmdict_fixture > 20
    st = jmdict.status(db)
    assert st["installed"] and st["dictionaries"][0]["entry_count"] == jmdict_fixture

    hits = lookup.lookup(db, "しょうがない")
    assert hits and hits[0].id == "1305510"
    assert "仕様がない" in hits[0].kanji and hits[0].is_expression
    assert hits[0].senses[0]["gloss_en"][0] == "there's no (other) way"

    ogoru = lookup.lookup(db, "奢る")[0]
    assert "奢る" in ogoru.kanji and ogoru.usually_kana and ogoru.headword == "おごる"
    assert lookup.lookup(db, "大丈夫")[0].headword == "大丈夫"  # not usually-kana → kanji form
    assert lookup.lookup(db, "存在しない語") == []


def test_reimport_replaces_previous_dictionary(db, jmdict_fixture):
    jmdict.import_json(db, JMDICT_FIXTURE_FILE)
    st = jmdict.status(db)
    assert len(st["dictionaries"]) == 1
    assert len(lookup.lookup(db, "奢る")) == 1


def test_candidates_for_conjugated_token(db, jmdict_fixture):
    tok = next(t for t in tokenize("今日は俺が奢ってやるよ") if t.surface == "奢っ")
    cands = lookup.candidates_for_token(db, tok)
    assert cands and cands[0].id == "1565940"


def test_expression_grouping_requires_matching_reading(db, jmdict_fixture):
    idx = expressions.get_index(db)
    tokens = tokenize("しょうがないなぁ…今日は俺が奢ってやるよ。")
    spans = expressions.group(tokens, idx.readings_for)
    texts = [s.text for s in spans]
    assert "しょうがない" in texts
    # 今日+は must NOT become こんにちは (reading mismatch)
    assert "今日は" not in texts


def test_dict_api(client, jmdict_fixture):
    r = client.get("/api/dict/lookup", params={"q": "大丈夫"})
    assert r.status_code == 200
    entries = r.json()["entries"]
    assert entries[0]["headword"] == "大丈夫" and entries[0]["reading"] == "だいじょうぶ"
    st = client.get("/api/dict/status").json()
    assert st["installed"] is True and st["install"]["state"] == "idle"
