def _setup(client):
    src = client.post("/api/sources", json={"title": "テスト作品", "kind": "game"}).json()
    ses = client.post("/api/sessions", json={"source_id": src["id"], "mode": "companion"}).json()
    return src, ses


def test_source_crud(client):
    r = client.post("/api/sources", json={"title": "Summer Pockets", "kind": "game"})
    assert r.status_code == 201
    sid = r.json()["id"]
    r = client.patch(
        f"/api/sources/{sid}", json={"region": {"left": 1, "top": 2, "width": 3, "height": 4}}
    )
    assert r.json()["region"] == {"left": 1, "top": 2, "width": 3, "height": 4}
    assert client.get("/api/sources").json()[0]["title"] == "Summer Pockets"
    assert client.delete(f"/api/sources/{sid}").status_code == 204
    assert client.get(f"/api/sources/{sid}").status_code == 404


def test_line_dedup_within_session(client):
    src, ses = _setup(client)
    body = {"session_id": ses["id"], "text": "え・・・本当に？", "origin": "ocr"}
    r1 = client.post("/api/lines", json=body)
    assert r1.status_code == 201 and r1.json()["duplicate"] is False
    assert r1.json()["line"]["text"] == "え…本当に？"
    assert r1.json()["line"]["source_id"] == src["id"]

    r2 = client.post("/api/lines", json={**body, "text": "え…本当に？"})
    assert r2.status_code == 200 and r2.json()["duplicate"] is True
    assert r2.json()["line"]["id"] == r1.json()["line"]["id"]

    # near duplicate (OCR partial line followed by the full line) keeps the longer text
    r3 = client.post("/api/lines", json={**body, "text": "え…本当に？じゃ"})
    assert r3.status_code == 200 and r3.json()["line"]["text"] == "え…本当に？じゃ"

    r4 = client.post("/api/lines", json={**body, "text": "今日は俺が奢ってやるよ。"})
    assert r4.status_code == 201
    assert len(client.get("/api/lines", params={"session_id": ses["id"]}).json()) == 2


def test_line_update_and_delete(client):
    _, ses = _setup(client)
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": "テスト"}).json()[
        "line"
    ]
    r = client.patch(f"/api/lines/{line['id']}", json={"status": "kept", "text": "テスト２"})
    assert r.json()["status"] == "kept" and r.json()["text"] == "テスト２"
    assert client.delete(f"/api/lines/{line['id']}").status_code == 204
    assert client.get(f"/api/lines/{line['id']}").status_code == 404


def test_session_end_records_stats(client):
    _, ses = _setup(client)
    assert client.get("/api/sessions/active").json()["id"] == ses["id"]
    client.post("/api/lines", json={"session_id": ses["id"], "text": "一"})
    client.post("/api/lines", json={"session_id": ses["id"], "text": "二"})
    r = client.post(f"/api/sessions/{ses['id']}/end")
    assert r.json()["ended_at"] is not None
    assert r.json()["stats"]["lines_total"] == 2
    assert client.get("/api/sessions/active").json() is None


def test_analyze_line(client, jmdict_fixture):
    _, ses = _setup(client)
    text = "しょうがないなぁ…今日は俺が奢ってやるよ。"
    line = client.post("/api/lines", json={"session_id": ses["id"], "text": text}).json()["line"]
    r = client.post(f"/api/lines/{line['id']}/analyze")
    assert r.status_code == 200
    body = r.json()
    ogoru = next(t for t in body["tokens"] if t["surface"] == "奢っ")
    assert ogoru["candidates"][0]["id"] == "1565940"
    assert ogoru["known_status"] is None and ogoru["term_id"] is None
    assert [s["text"] for s in body["spans"]] == ["しょうがない"]
    assert body["spans"][0]["candidates"][0]["id"] == "1305510"
    assert body["contractions"][0]["form"] == "しょうがない"
    # second call is served from the cache and still carries learner state fields
    assert (
        client.post(f"/api/lines/{line['id']}/analyze").json()["tokens"][0]["known_status"] is None
    )


def test_dedup_rules_unit():
    from kotoba.services import dedup

    assert dedup.is_growth("え…", "え…本当に？")
    assert dedup.is_growth("え…本当に？", "え…")
    assert not dedup.is_growth("え…本当に？", "今日は")
    assert dedup.similarity("今日は俺が奢ってやるよ", "今日は俺が奢ってやるょ") >= 0.9
