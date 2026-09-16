from kotoba.schemas.lines import line_locator

SRT = "1\n00:00:01,500 --> 00:00:03,000\nこんにちは\n\n2\n00:00:04,000 --> 00:00:06,000\nまたね\n"


def make_session(client) -> int:
    src = client.post("/api/sources", json={"title": "作品"}).json()
    return client.post("/api/sessions", json={"source_id": src["id"]}).json()["id"]


def test_old_fields_still_read_as_a_locator(client):
    session_id = make_session(client)
    time_line = client.post(
        "/api/lines",
        json={"session_id": session_id, "text": "時間", "start_ms": 1500, "end_ms": 3000},
    ).json()["line"]
    assert time_line["locator"] == {"kind": "time", "start_ms": 1500, "end_ms": 3000}

    region_line = client.post(
        "/api/lines",
        json={
            "session_id": session_id,
            "text": "画面",
            "position": {"region": {"left": 1, "top": 2, "width": 3, "height": 4}},
        },
    ).json()["line"]
    assert region_line["locator"] == {
        "kind": "region",
        "region": {"left": 1, "top": 2, "width": 3, "height": 4},
    }

    assert (
        client.post("/api/lines", json={"session_id": session_id, "text": "無"}).json()["line"][
            "locator"
        ]
        is None
    )


def test_locator_json_wins_over_the_old_fields(client):
    session_id = make_session(client)
    line = client.post(
        "/api/lines",
        json={
            "session_id": session_id,
            "text": "ページ",
            "start_ms": 1500,
            "locator": {"kind": "page", "page": 12, "box": [1, 2, 3, 4]},
        },
    ).json()["line"]
    assert line["locator"] == {"kind": "page", "page": 12, "box": [1, 2, 3, 4]}


def test_ord_orders_lines_without_captured_at(client):
    session_id = make_session(client)
    ids = {}
    for word, order in (("三", 3), ("一", 1), ("二", 2)):
        ids[order] = client.post(
            "/api/lines",
            json={"session_id": session_id, "text": word, "ord": order},
        ).json()["line"]["id"]

    rows = client.get("/api/lines", params={"session_id": session_id}).json()
    assert [row["id"] for row in rows] == [ids[1], ids[2], ids[3]]
    assert [row["ord"] for row in rows] == [1, 2, 3]


def test_subtitle_import_writes_ordered_locators(client):
    src = client.post("/api/sources", json={"title": "字幕作品"}).json()
    r = client.post(
        f"/api/sources/{src['id']}/subtitles",
        files={"file": ("a.srt", SRT.encode("utf-8"), "text/plain")},
    )
    session_id = r.json()["session_id"]
    lines = client.get("/api/lines", params={"session_id": session_id}).json()
    assert [line["ord"] for line in lines] == [1, 2]
    assert lines[0]["locator"] == {"kind": "time", "start_ms": 1500, "end_ms": 3000}
    assert lines[1]["locator"] == {"kind": "time", "start_ms": 4000, "end_ms": 6000}


def test_line_locator_handles_broken_json():
    class FakeLine:
        locator_json = "{not json"
        start_ms = None
        end_ms = None
        position_json = None

    assert line_locator(FakeLine()) is None
