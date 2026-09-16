SRT = (
    "1\n00:00:01,500 --> 00:00:03,000\nこんにちは\n\n"
    "2\n00:00:04,000 --> 00:00:06,000\nまたね\n\n"
    "3\n00:00:07,000 --> 00:00:08,000\nこんにちは\n"
)

ASS = (
    "[Events]\n"
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    "Dialogue: 0,0:00:01.50,0:00:03.00,Default,アリス,0,0,0,,こんにちは\n"
)


def upload(client, source_id, data, filename="test.srt"):
    return client.post(
        f"/api/sources/{source_id}/subtitles",
        files={"file": (filename, data, "text/plain")},
    )


def make_source(client) -> int:
    return client.post("/api/sources", json={"title": "作品"}).json()["id"]


def test_import_srt_creates_an_import_session_with_timed_lines(client):
    source_id = make_source(client)
    r = upload(client, source_id, SRT.encode("utf-8"))
    assert r.status_code == 200
    body = r.json()
    assert body["created"] == 2 and body["skipped"] == 1

    session = client.get(f"/api/sessions/{body['session_id']}").json()
    assert session["mode"] == "import"
    assert session["text_source"] == "subtitle"
    assert session["source_id"] == source_id

    lines = client.get("/api/lines", params={"session_id": body["session_id"]}).json()
    assert len(lines) == 2
    by_text = {line["text"]: line for line in lines}
    assert set(by_text) == {"こんにちは", "またね"}
    assert by_text["こんにちは"]["origin"] == "subtitle"
    assert (by_text["こんにちは"]["start_ms"], by_text["こんにちは"]["end_ms"]) == (1500, 3000)
    assert (by_text["またね"]["start_ms"], by_text["またね"]["end_ms"]) == (4000, 6000)


def test_import_ass_keeps_the_speaker(client):
    source_id = make_source(client)
    r = upload(client, source_id, ASS.encode("utf-8-sig"), filename="test.ass")
    assert r.status_code == 200
    lines = client.get("/api/lines", params={"session_id": r.json()["session_id"]}).json()
    assert len(lines) == 1
    assert lines[0]["speaker"] == "アリス"
    assert (lines[0]["start_ms"], lines[0]["end_ms"]) == (1500, 3000)


def test_import_accepts_shift_jis(client):
    source_id = make_source(client)
    r = upload(client, source_id, "1\n00:00:01,000 --> 00:00:02,000\nおはよう\n".encode("cp932"))
    assert r.status_code == 200
    assert r.json()["created"] == 1


def test_import_rejects_undecodable_files(client):
    source_id = make_source(client)
    r = upload(client, source_id, b"\x81 ")
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_encoding"


def test_import_rejects_a_file_without_cues(client):
    source_id = make_source(client)
    r = upload(client, source_id, "这不是字幕".encode())
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_subtitle"


def test_import_unknown_source(client):
    r = upload(client, 999, SRT.encode("utf-8"))
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
