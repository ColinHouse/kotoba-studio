from kotoba.services import learning


def _line(client, session_id, text):
    return client.post("/api/lines", json={"session_id": session_id, "text": text}).json()["line"]


def _setup(client, title="作品A"):
    src = client.post("/api/sources", json={"title": title}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    return src, ses


def test_same_word_twice_is_one_term_with_two_encounters(client, db):
    _, ses = _setup(client)
    l1 = _line(client, ses["id"], "今日は俺が奢ってやるよ。")
    l2 = _line(client, ses["id"], "また奢ってくれるの？")
    body = {
        "headword": "奢る",
        "reading": "おごる",
        "surface": "奢っ",
        "pos": "v5r",
        "sense": {"gloss_en": "to treat (someone) to (something)", "gloss_zh": "请客"},
    }
    r1 = client.post(
        "/api/encounters", json={**body, "line_id": l1["id"], "span_start": 4, "span_end": 6}
    )
    r2 = client.post(
        "/api/encounters", json={**body, "line_id": l2["id"], "span_start": 2, "span_end": 4}
    )
    assert r1.status_code == 201 and r2.status_code == 201
    assert r1.json()["term"]["id"] == r2.json()["term"]["id"]
    term = client.get(f"/api/terms/{r1.json()['term']['id']}").json()
    assert term["encounter_count"] == 2 and term["source_count"] == 1
    assert len(term["senses"]) == 1  # same gloss reused, not duplicated
    assert [e["line_text"] for e in term["encounters"]] == [l1["text"], l2["text"]]
    # lines with a confirmed encounter leave the inbox
    assert client.get(f"/api/lines/{l1['id']}").json()["status"] == "kept"
    assert client.get(f"/api/lines/{l1['id']}").json()["encounter_count"] == 1


def test_cards_are_unique_per_term_and_type(client):
    _, ses = _setup(client)
    line = _line(client, ses["id"], "勉強しなきゃ。")
    enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "勉強",
            "reading": "べんきょう",
            "surface": "勉強",
            "card_types": ["reading", "meaning"],
        },
    ).json()
    assert [c["card_type"] for c in enc["cards"]] == ["reading", "meaning"]
    assert enc["cards"][0]["review_owner"] == "desktop"  # no phone registered yet
    again = client.post(
        "/api/cards",
        json={"encounter_id": enc["encounter"]["id"], "card_types": ["reading", "cloze"]},
    ).json()
    assert len(client.get("/api/cards", params={"term_id": enc["term"]["id"]}).json()) == 3
    assert again[0]["id"] == enc["cards"][0]["id"]
    assert client.get(f"/api/terms/{enc['term']['id']}").json()["known_status"] == "learning"
    bad = client.post(
        "/api/cards", json={"encounter_id": enc["encounter"]["id"], "card_types": ["nope"]}
    )
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "invalid_card_type"


def test_homograph_trap_and_contraction(client):
    assert learning.homograph_trap("勉強")["ja_meaning"].startswith("学习")
    assert learning.homograph_trap("奢る") is None
    _, ses = _setup(client)
    line = _line(client, ses["id"], "食べちゃった。")
    enc = client.post(
        "/api/encounters",
        json={"line_id": line["id"], "headword": "てしまう", "surface": "ちゃった"},
    ).json()
    assert enc["encounter"]["contraction_of"] == "てしまった"
    trap_enc = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "勉強",
            "reading": "べんきょう",
            "surface": "勉強",
        },
    ).json()
    assert trap_enc["term"]["trap"]["zh_reading_meaning"].startswith("勉强")


def test_term_search_status_and_bulk(client):
    _, ses = _setup(client)
    line = _line(client, ses["id"], "猫が好き。")
    client.post(
        "/api/encounters",
        json={"line_id": line["id"], "headword": "猫", "reading": "ねこ", "surface": "猫"},
    )
    assert client.get("/api/terms", params={"q": "ね"}).json()[0]["headword"] == "猫"
    tid = client.get("/api/terms", params={"q": "猫"}).json()[0]["id"]
    assert (
        client.patch(f"/api/terms/{tid}", json={"known_status": "known"}).json()["known_status"]
        == "known"
    )
    assert client.get("/api/terms", params={"status": "known"}).json()[0]["id"] == tid
    r = client.post("/api/terms/bulk-known", json={"headwords": ["犬", "猫", "鳥"]})
    assert r.json()["updated"] == 3
    assert len(client.get("/api/terms", params={"status": "known"}).json()) == 3
    stats = client.get("/api/cards/stats").json()
    assert stats["total"] == 0 and stats["due_now"] == 0


def test_analyze_reflects_learner_state(client, jmdict_fixture):
    _, ses = _setup(client)
    line = _line(client, ses["id"], "今日は俺が奢ってやるよ。")
    client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "奢る",
            "reading": "おごる",
            "surface": "奢っ",
            "card_types": ["reading"],
        },
    )
    body = client.post(f"/api/lines/{line['id']}/analyze").json()
    ogoru = next(t for t in body["tokens"] if t["surface"] == "奢っ")
    assert ogoru["known_status"] == "learning" and ogoru["encountered"] is True
