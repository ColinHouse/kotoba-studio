from kotoba.models import Card


def _confirm(
    client, session_id, text, headword, reading, surface, gloss_zh=None, types=("reading", "cloze")
):
    line = client.post("/api/lines", json={"session_id": session_id, "text": text}).json()["line"]
    body = {
        "line_id": line["id"],
        "headword": headword,
        "reading": reading,
        "surface": surface,
        "span_start": text.index(surface),
        "span_end": text.index(surface) + len(surface),
        "card_types": list(types),
    }
    if gloss_zh:
        body["sense"] = {"gloss_zh": gloss_zh}
    return client.post("/api/encounters", json=body).json()


def test_quiz_roundtrip_and_summary(client, db):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    enc = _confirm(
        client, ses["id"], "今日は俺が奢ってやるよ。", "奢る", "おごる", "奢っ", gloss_zh="请客"
    )

    r = client.post(f"/api/quiz/sessions/{ses['id']}", params={"kinds": "reading,cloze,meaning"})
    assert r.status_code == 200
    items = {i["kind"]: i for i in r.json()["items"]}
    assert set(items) == {"reading", "cloze", "meaning"}
    assert (
        items["reading"]["answer"] is None
        and items["reading"]["prompt"] == "今日は俺が奢ってやるよ。"
    )
    assert items["cloze"]["prompt"] == "今日は俺が＿＿てやるよ。"
    assert items["meaning"]["answer"] == "请客"  # self-graded, so the answer is included

    card_id = items["reading"]["card_id"]
    before = db.get(Card, card_id).due
    base = {"session_id": ses["id"], "encounter_id": enc["encounter"]["id"]}
    a1 = client.post(
        "/api/quiz/answers", json={**base, "card_id": card_id, "kind": "reading", "given": "オゴル"}
    ).json()
    assert a1["correct"] is True and a1["expected"] == "おごる"
    a2 = client.post(
        "/api/quiz/answers",
        json={**base, "card_id": items["cloze"]["card_id"], "kind": "cloze", "given": "奢る"},
    ).json()
    assert a2["correct"] is True
    a3 = client.post(
        "/api/quiz/answers",
        json={**base, "card_id": items["meaning"]["card_id"], "kind": "meaning", "correct": False},
    ).json()
    assert a3["correct"] is False
    db.expire_all()
    assert db.get(Card, card_id).due == before  # quiz never schedules

    summary = client.get(f"/api/sessions/{ses['id']}/summary").json()
    assert summary["lines_total"] == 1 and summary["kept"] == 1
    assert [t["headword"] for t in summary["new_terms"]] == ["奢る"] and summary[
        "seen_again_terms"
    ] == []
    assert summary["cards_created"] == 2
    assert summary["quiz"] == {"answered": 3, "correct": 2}


def test_summary_detects_words_seen_again(client):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    s1 = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    _confirm(client, s1["id"], "猫が好き。", "猫", "ねこ", "猫")
    src2 = client.post("/api/sources", json={"title": "作品2"}).json()
    s2 = client.post("/api/sessions", json={"source_id": src2["id"]}).json()
    _confirm(client, s2["id"], "この猫は誰の？", "猫", "ねこ", "猫", types=())
    summary = client.get(f"/api/sessions/{s2['id']}/summary").json()
    assert summary["new_terms"] == [] and [t["headword"] for t in summary["seen_again_terms"]] == [
        "猫"
    ]
    assert summary["cards_created"] == 0
    assert client.get("/api/terms", params={"q": "猫"}).json()[0]["source_count"] == 2


def test_quiz_skips_terms_without_cards_and_validates_kind(client):
    src = client.post("/api/sources", json={"title": "作品"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"]}).json()
    _confirm(client, ses["id"], "犬が好き。", "犬", "いぬ", "犬", types=())
    assert client.post(f"/api/quiz/sessions/{ses['id']}").json()["items"] == []
    assert (
        client.post(f"/api/quiz/sessions/{ses['id']}", params={"kinds": "nope"}).status_code == 400
    )
