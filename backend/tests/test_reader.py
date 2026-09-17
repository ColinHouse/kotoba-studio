import io
import json
import zipfile

BOX = [10, 20, 110, 220]


def block(lines, box=None):
    return {
        "box": box or BOX,
        "vertical": True,
        "font_size": 26,
        "lines_coords": [[[0, 0], [20, 0], [20, 100], [0, 100]] for _ in lines],
        "lines": lines,
    }


def mokuro_json(pages) -> bytes:
    volume = {"version": "0.2.5", "title": "漫画", "volume": "vol1", "pages": pages}
    return json.dumps(volume).encode()


def page(blocks, width=827, height=1170) -> dict:
    return {"version": "0.2.5", "img_width": width, "img_height": height, "blocks": blocks}


def volume_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return buf.getvalue()


def make_source(client) -> int:
    return client.post("/api/sources", json={"title": "漫画作品", "kind": "manga"}).json()["id"]


def import_volume(client, source_id: int, files: dict[str, bytes]) -> int:
    r = client.post(
        f"/api/sources/{source_id}/mokuro",
        files={"file": ("vol1.zip", volume_zip(files), "application/zip")},
    )
    assert r.status_code == 200, r.text
    return r.json()["session_id"]


def test_pages_group_blocks_in_reading_order(client):
    source_id = make_source(client)
    import_volume(
        client,
        source_id,
        {
            "vol1.mokuro": mokuro_json(
                [
                    page([block(["いち"]), block(["に"])]),
                    page([block(["さん"])]),
                ]
            ),
            "0001.jpg": b"one",
            "0002.jpg": b"two",
        },
    )

    r = client.get(f"/api/sources/{source_id}/pages")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_id"] == source_id and body["title"] == "漫画作品"
    assert [p["page"] for p in body["pages"]] == [1, 2]
    assert [b["text"] for b in body["pages"][0]["blocks"]] == ["いち", "に"]
    assert [b["text"] for b in body["pages"][1]["blocks"]] == ["さん"]

    first = body["pages"][0]["blocks"][0]
    assert first["box"] == BOX
    assert first["status"] == "inbox"
    assert first["encounter_count"] == 0 and first["card_count"] == 0
    assert body["pages"][0]["image"].startswith("manga/")
    assert body["pages"][0]["image"].endswith("0001.jpg")
    assert body["pages"][1]["image"].endswith("0002.jpg")


def test_pages_mark_lines_that_already_have_a_card(client):
    source_id = make_source(client)
    session_id = import_volume(
        client, source_id, {"vol1.mokuro": mokuro_json([page([block(["いち"])])])}
    )
    line = client.get("/api/lines", params={"session_id": session_id}).json()[0]

    r = client.post(
        "/api/encounters",
        json={
            "line_id": line["id"],
            "headword": "いち",
            "reading": "いち",
            "surface": "いち",
            "card_types": ["meaning"],
        },
    )
    assert r.status_code == 201, r.text

    body = client.get(f"/api/sources/{source_id}/pages").json()
    assert body["pages"][0]["blocks"][0]["card_count"] == 1
    assert body["pages"][0]["blocks"][0]["encounter_count"] == 1


def test_pages_count_cards_not_encounters(client):
    source_id = make_source(client)
    session_id = import_volume(
        client, source_id, {"vol1.mokuro": mokuro_json([page([block(["いち"])])])}
    )
    line = client.get("/api/lines", params={"session_id": session_id}).json()[0]
    client.post(
        "/api/encounters",
        json={"line_id": line["id"], "headword": "いち", "card_types": []},
    )

    body = client.get(f"/api/sources/{source_id}/pages").json()
    assert body["pages"][0]["blocks"][0]["card_count"] == 0
    assert body["pages"][0]["blocks"][0]["encounter_count"] == 1


def test_pages_only_include_page_located_lines(client):
    source_id = make_source(client)
    client.post("/api/lines", json={"source_id": source_id, "text": "とりあえず"})
    body = client.get(f"/api/sources/{source_id}/pages").json()
    assert body["pages"] == []


def test_pages_from_a_text_only_import_have_no_image(client):
    source_id = make_source(client)
    import_volume(client, source_id, {"vol1.mokuro": mokuro_json([page([block(["いち"])])])})
    body = client.get(f"/api/sources/{source_id}/pages").json()
    assert body["pages"][0]["image"] is None
    assert body["pages"][0]["blocks"][0]["text"] == "いち"


def test_pages_unknown_source(client):
    r = client.get("/api/sources/999/pages")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "not_found"
